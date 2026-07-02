"""Tests for the pure logic in utils.py: ground truth construction,
pairwise metrics, clustering, and the threshold filter."""
import os

from PIL import Image

import config
from utils import (calculate_wasted_space, filter_at_threshold,
                   format_file_size, generate_ground_truth, norm_path,
                   organize_clusters, pair_key, pair_metrics, source_id,
                   walk_image_files)


# ----------------------------------------------------------------- paths

def test_pair_key_is_symmetric():
    assert pair_key("a/x.jpg", "b/y.jpg") == pair_key("b/y.jpg", "a/x.jpg")


def test_walk_skips_trash_folder(tmp_path):
    (tmp_path / "x.jpg").write_bytes(b"")
    trash = tmp_path / config.TRASH_DIR_NAME
    trash.mkdir()
    (trash / "y.jpg").write_bytes(b"")

    found = [os.path.basename(f) for f in walk_image_files(str(tmp_path))]
    assert found == ["x.jpg"]


def test_walk_filters_by_extension(tmp_path):
    (tmp_path / "a.jpg").write_bytes(b"")
    (tmp_path / "b.txt").write_bytes(b"")
    found = [os.path.basename(f) for f in walk_image_files(str(tmp_path))]
    assert found == ["a.jpg"]


# ----------------------------------------------------------- ground truth

def test_source_id_conventions():
    # copydays convention: same basename in different folders
    assert source_id("original/200000.jpg") == "200000"
    assert source_id("jpeg/10/200000.jpg") == "200000"
    # generated convention: _aug_* suffix
    assert source_id("berlin_1_aug_crop.jpg") == "berlin_1"
    assert source_id("berlin_1_AUG_ROT.png") == "berlin_1"
    # a plain name maps to itself
    assert source_id("holiday_photo.jpg") == "holiday_photo"


def test_ground_truth_builds_full_pair_closure(tmp_path):
    # a: 3 copies -> 3 pairs; b: 2 copies -> 1 pair; c: unique -> excluded
    for rel in ["original/a.jpg", "jpeg/10/a.jpg", "crops/50/a.jpg",
                "original/b.jpg", "jpeg/10/b.jpg", "original/c.jpg"]:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"")

    groups, gt_pairs = generate_ground_truth(str(tmp_path))
    assert set(groups) == {"a", "b"}
    assert len(groups["a"]) == 3
    assert len(gt_pairs) == 3 + 1


def test_ground_truth_none_without_structure(tmp_path):
    for name in ["cat.jpg", "dog.jpg", "bird.jpg"]:
        (tmp_path / name).write_bytes(b"")
    groups, gt_pairs = generate_ground_truth(str(tmp_path))
    assert groups is None and gt_pairs is None


# ----------------------------------------------------------------- metrics

def test_pair_metrics_counts():
    gt = {("a", "b"), ("c", "d"), ("e", "f")}
    det = {("a", "b"), ("x", "y")}
    m = pair_metrics(det, gt)
    assert (m["tp"], m["fp"], m["fn"]) == (1, 1, 2)
    assert m["precision"] == 0.5
    assert m["recall"] == 1 / 3
    assert abs(m["f1"] - 0.4) < 1e-9


def test_pair_metrics_empty_detections():
    m = pair_metrics(set(), {("a", "b")})
    assert m["precision"] == m["recall"] == m["f1"] == 0.0


def test_pair_metrics_restrict_requires_both_endpoints():
    gt = {("a", "b"), ("a", "c")}
    det = {("a", "b"), ("a", "c")}
    m = pair_metrics(det, gt, restrict={"a", "b"})
    # only (a, b) survives the restriction on either side
    assert (m["tp"], m["fp"], m["fn"]) == (1, 0, 0)
    assert m["f1"] == 1.0


# -------------------------------------------------------------- clustering

def _make_image(path, size):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, (120, 40, 200)).save(path)
    return str(path)


def test_clusters_are_connected_components(tmp_path):
    a = _make_image(tmp_path / "a.png", (4, 4))
    b = _make_image(tmp_path / "b.png", (2, 2))
    c = _make_image(tmp_path / "c.png", (2, 2))
    d = _make_image(tmp_path / "d.png", (2, 2))
    e = _make_image(tmp_path / "e.png", (2, 2))

    clusters = organize_clusters([
        {"file1": a, "file2": b, "score": 0.9},
        {"file1": b, "file2": c, "score": 0.8},
        {"file1": d, "file2": e, "score": 0.7},
    ])
    assert len(clusters) == 2
    # sorted by size: {a,b,c} before {d,e}
    assert len(clusters[0]["duplicates"]) == 2
    assert len(clusters[1]["duplicates"]) == 1


def test_keeper_is_highest_resolution(tmp_path):
    small = _make_image(tmp_path / "small.png", (2, 2))
    big = _make_image(tmp_path / "big.png", (4, 4))
    clusters = organize_clusters([{"file1": small, "file2": big, "score": 0.9}])
    assert clusters[0]["original"] == big


def test_keeper_prefers_original_folder_hint(tmp_path):
    hinted = _make_image(tmp_path / "original" / "x.png", (2, 2))
    other = _make_image(tmp_path / "copies" / "x.png", (4, 4))
    clusters = organize_clusters([{"file1": other, "file2": hinted, "score": 0.9}])
    assert clusters[0]["original"] == hinted


def test_indirect_member_scored_by_path_average(tmp_path):
    a = _make_image(tmp_path / "a.png", (4, 4))
    b = _make_image(tmp_path / "b.png", (2, 2))
    c = _make_image(tmp_path / "c.png", (2, 2))
    clusters = organize_clusters([
        {"file1": a, "file2": b, "score": 0.9},
        {"file1": b, "file2": c, "score": 0.5},
    ])
    scores = {d["path"]: d["score"] for d in clusters[0]["duplicates"]}
    assert scores[b] == 0.9
    assert abs(scores[c] - 0.7) < 1e-9  # mean of the a-b-c path


# ----------------------------------------------------------------- filters

def test_filter_never_hides_hash_pairs():
    dups = [
        {"file1": "a", "file2": "b", "score": 0.30, "method": "dHash"},
        {"file1": "c", "file2": "d", "score": 0.60, "method": "DINOv2"},
        {"file1": "e", "file2": "f", "score": 0.95, "method": "DINOv2"},
    ]
    kept = filter_at_threshold(dups, 0.9)
    methods = {(d["file1"], d["method"]) for d in kept}
    assert ("a", "dHash") in methods
    assert ("e", "DINOv2") in methods
    assert len(kept) == 2


def test_wasted_space_counts_each_copy_once(tmp_path):
    keep = tmp_path / "keep.bin"
    dup = tmp_path / "dup.bin"
    keep.write_bytes(b"x" * 100)
    dup.write_bytes(b"y" * 2048)

    clusters = [
        {"original": str(keep), "duplicates": [{"path": str(dup), "score": 0.9}]},
        # same duplicate appearing again must not double-count
        {"original": str(keep), "duplicates": [{"path": str(dup), "score": 0.8}]},
    ]
    mb = calculate_wasted_space(clusters)
    assert abs(mb - 2048 / (1024 * 1024)) < 1e-9


def test_format_file_size_units():
    assert format_file_size(512) == "512.00 B"
    assert format_file_size(2048) == "2.00 KB"
    assert format_file_size(5 * 1024 ** 2) == "5.00 MB"
