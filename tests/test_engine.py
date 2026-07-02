"""Tests for the detection engine using a fake backbone: hashing, FAISS
range search, pair merging, delete/undo, and threshold calibration run
exactly as in production, but no model is ever downloaded."""
import numpy as np

import config
from engine import DuplicateDetector
from utils import norm_path, pair_key

DIM = 8
HASH_BYTES = (config.HASH_SIZE ** 2) // 8


class _DummyConfig:
    hidden_size = DIM


class _DummyModel:
    config = _DummyConfig()


def make_detector():
    return DuplicateDetector("fake-model", backbone=(None, _DummyModel(), "cpu"))


def unit(*components):
    """A unit-norm float32 vector from the first few components."""
    v = np.zeros(DIM, dtype="float32")
    v[:len(components)] = components
    return v / np.linalg.norm(v)


def load(det, files, embeddings, hash_bits):
    det.load_precomputed(np.stack(embeddings), files, np.stack(hash_bits))


def hash_of(*flip_bits):
    """A 256-bit hash with the given bit positions flipped from zero."""
    bits = np.zeros(HASH_BYTES, dtype="uint8")
    for b in flip_bits:
        bits[b // 8] |= 1 << (b % 8)
    return bits


ORTHO = [unit(1), unit(0, 1), unit(0, 0, 1)]  # mutually orthogonal


# --------------------------------------------------------- stage 1: hashing

def test_hash_stage_finds_identical_and_near_hashes():
    det = make_detector()
    # f0 == f1 exactly, f2 within threshold (2 bits), f3 out of reach (3 bits)
    load(det, ["f0", "f1", "f2", "f3"],
         [ORTHO[0], ORTHO[1], ORTHO[2], unit(0, 0, 0, 1)],
         [hash_of(), hash_of(), hash_of(0, 1), hash_of(10, 20, 30)])

    found = {pair_key(p["file1"], p["file2"]): p["hash_distance"]
             for p in det.fast_duplicates}
    assert found[pair_key("f0", "f1")] == 0
    assert found[pair_key("f0", "f2")] == 2
    assert found[pair_key("f1", "f2")] == 2
    assert pair_key("f0", "f3") not in found
    assert len(found) == 3


def test_hash_pair_score_reflects_distance():
    det = make_detector()
    load(det, ["f0", "f1"], [ORTHO[0], ORTHO[1]], [hash_of(), hash_of(5)])
    (pair,) = det.fast_duplicates
    assert pair["hash_distance"] == 1
    assert abs(pair["score"] - (1.0 - 1 / config.HASH_SIZE ** 2)) < 1e-9
    assert pair["method"] == "dHash"


# -------------------------------------------------------- stage 2: semantic

def test_semantic_pairs_from_range_search():
    det = make_detector()
    v0 = unit(1)
    v1 = unit(0.9, np.sqrt(1 - 0.81))  # cosine 0.9 with v0
    v2 = unit(0, 0, 1)                 # orthogonal to both
    load(det, ["f0", "f1", "f2"], [v0, v1, v2],
         [hash_of(), hash_of(100), hash_of(200, 201, 202)])

    assert len(det.semantic_pairs) == 1
    (pair,) = det.semantic_pairs
    assert pair_key(pair["file1"], pair["file2"]) == pair_key("f0", "f1")
    assert abs(pair["score"] - 0.9) < 1e-5
    assert pair["method"] == "DINOv2"


def test_find_duplicates_respects_threshold_but_keeps_hash_pairs():
    det = make_detector()
    v0 = unit(1)
    v1 = unit(0.9, np.sqrt(1 - 0.81))
    # f2/f3: hash-identical but visually unrelated to everything.
    # f0/f1 hashes sit far (4+ bits) from every other hash.
    load(det, ["f0", "f1", "f2", "f3"],
         [v0, v1, ORTHO[2], unit(0, 0, 0, 1)],
         [hash_of(30, 31, 32, 33), hash_of(60, 61, 62, 63),
          hash_of(), hash_of()])

    at_low = {pair_key(p["file1"], p["file2"]) for p in det.find_duplicates(0.5)}
    assert at_low == {pair_key("f0", "f1"), pair_key("f2", "f3")}

    # raising the cosine threshold drops the semantic pair, never the hash pair
    at_high = {pair_key(p["file1"], p["file2"]) for p in det.find_duplicates(0.95)}
    assert at_high == {pair_key("f2", "f3")}


def test_find_duplicates_does_not_double_count_overlapping_pairs():
    det = make_detector()
    v0 = unit(1)
    v1 = unit(0.99, np.sqrt(1 - 0.99 ** 2))
    # same pair is both hash-identical and semantically similar
    load(det, ["f0", "f1"], [v0, v1], [hash_of(), hash_of()])

    results = det.find_duplicates(0.5)
    assert len(results) == 1


# --------------------------------------------------------- delete / restore

def test_remove_and_restore_files_round_trip():
    det = make_detector()
    v0 = unit(1)
    v1 = unit(0.9, np.sqrt(1 - 0.81))
    load(det, ["f0", "f1", "f2"], [v0, v1, ORTHO[2]],
         [hash_of(1), hash_of(2, 3, 4), hash_of(5, 6, 7)])
    assert len(det.semantic_pairs) == 1

    payload = det.remove_files(["f1"])
    assert det.index.ntotal == 2
    assert "f1" not in det.stored_files
    assert det.semantic_pairs == []

    det.restore_files(payload)
    assert det.index.ntotal == 3
    assert "f1" in det.stored_files
    assert len(det.semantic_pairs) == 1


def test_remove_unknown_path_is_a_noop():
    det = make_detector()
    load(det, ["f0", "f1"], [ORTHO[0], ORTHO[1]], [hash_of(1), hash_of(2, 3, 4)])
    assert det.remove_files(["nonexistent"]) is None
    assert det.index.ntotal == 2


# ------------------------------------------------------------- calibration

def test_calibration_picks_separating_threshold_and_scores_holdout():
    det = make_detector()

    files = {g: (f"data/{g}1.jpg", f"data/{g}2.jpg") for g in "abcd"}
    gt_groups = {g: {norm_path(f1), norm_path(f2)}
                 for g, (f1, f2) in files.items()}
    gt_pairs = {pair_key(f1, f2) for f1, f2 in files.values()}

    # every true pair detected with a distinct score, plus one false
    # positive across groups at 0.45
    det.fast_duplicates = []
    det.semantic_pairs = [
        {"file1": files["a"][0], "file2": files["a"][1], "score": 0.90, "method": "DINOv2"},
        {"file1": files["b"][0], "file2": files["b"][1], "score": 0.80, "method": "DINOv2"},
        {"file1": files["c"][0], "file2": files["c"][1], "score": 0.70, "method": "DINOv2"},
        {"file1": files["d"][0], "file2": files["d"][1], "score": 0.60, "method": "DINOv2"},
        {"file1": files["a"][0], "file2": files["b"][0], "score": 0.45, "method": "DINOv2"},
    ]

    result = det.calibrate_threshold(gt_groups, gt_pairs)

    # the chosen threshold must exclude the 0.45 false positive but keep
    # all four true pairs (scores 0.60+)
    assert 0.45 < result["threshold"] <= 0.60
    assert result["calibration_f1"] == 1.0
    assert result["holdout"]["f1"] == 1.0
    assert det.optimal_threshold == result["threshold"]

    assert result["n_groups"] == 4
    assert result["n_gt_pairs"] == 4
    # 0.40 .. 0.99 in steps of 0.01
    assert len(result["history"]) == 60
    # at the sweep floor everything is detected, including the false positive
    assert result["history"][0]["tp"] == 4
    assert result["history"][0]["fp"] == 1


def test_calibration_returns_none_without_ground_truth():
    det = make_detector()
    assert det.calibrate_threshold({}, set()) is None
