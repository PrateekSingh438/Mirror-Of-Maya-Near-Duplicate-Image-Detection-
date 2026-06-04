"""Offline indexer (CLI).

Runs where the dataset + (optionally) a GPU live. Embeds the corpus, builds a
FAISS index, calibrates the threshold against ground truth, clusters, and writes
a portable ./artifacts bundle the deployed app loads at boot.

    python -m indexer build --data ./dataset_copydays --out ./artifacts
    python -m indexer calibrate --artifacts ./artifacts
"""

import argparse
import json
import os
import sys

import faiss
import numpy as np
from PIL import Image
from tqdm import tqdm

import artifacts as art
from config import CFG
from dedup import (calibrate, cluster_pairs, find_semantic_pairs, identity_of,
                   pair_key, walk_image_files)
from embedder import embed_paths
from hashing import compute_dhash, find_hash_duplicates


def _ground_truth_for_ids(ids, id_to_path):
    groups = {}
    for i in ids:
        groups.setdefault(identity_of(id_to_path[i]), []).append(i)
    gt = set()
    for members in groups.values():
        for a in range(len(members)):
            for b in range(a + 1, len(members)):
                gt.add(pair_key(members[a], members[b]))
    return gt


def build(args):
    data_dir = args.data
    out_dir = args.out
    CFG.MODEL_ID = args.model
    CFG.POOLING = args.pooling

    paths = sorted(walk_image_files(data_dir))
    if not paths:
        sys.exit(f"No images found under {data_dir!r}")
    print(f"Found {len(paths)} images. Model={CFG.MODEL_ID} pooling={CFG.POOLING}")

    # Stage 1 — embed everything (every image stays searchable).
    print("Embedding...")
    bar = tqdm(total=len(paths), desc="embed")
    vectors, kept = embed_paths(paths, progress=lambda n: bar.update(n - bar.n))
    bar.close()
    if len(kept) == 0:
        sys.exit("No readable images embedded.")

    ids = [str(i) for i in range(len(kept))]
    id_to_path = dict(zip(ids, kept))

    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)
    print(f"Indexed {index.ntotal} vectors (dim={vectors.shape[1]})")

    # Stage 0 — dHash exact/near-exact pairs.
    print("Hashing...")
    hashes = [(i, compute_dhash(id_to_path[i])) for i in tqdm(ids, desc="dhash")]
    dhash_by_id = dict(hashes)
    hash_pairs = find_hash_duplicates(hashes)
    print(f"dHash exact/near-exact pairs: {len(hash_pairs)}")

    # Candidate pairs at the lowest calibration threshold, then calibrate.
    min_t = min(CFG.CALIBRATION_THRESHOLDS)
    print(f"Generating candidate pairs at t>={min_t}...")
    pairs = find_semantic_pairs(index, ids, threshold=min_t, top_k=args.top_k,
                                hash_pairs=hash_pairs)
    print(f"Candidate pairs: {len(pairs)}")

    gt = _ground_truth_for_ids(ids, id_to_path)
    print(f"Ground-truth positive pairs: {len(gt)}")
    best_t, best_f1, history = calibrate(pairs, gt)
    print(f"Optimal threshold={best_t:.2f}  F1={best_f1:.4f}")

    # Cluster at the chosen threshold.
    above = [p for p in pairs if p["score"] >= best_t]
    clusters = cluster_pairs(above, mode="semantic")
    cluster_of = {}
    for cid, c in enumerate(clusters):
        cluster_of[c["original"]] = cid
        for d in c["duplicates"]:
            cluster_of[d["id"]] = cid

    # Metadata + thumbnails in a single pass.
    print("Writing metadata + thumbnails...")
    rows = []
    for i in tqdm(ids, desc="meta"):
        path = id_to_path[i]
        try:
            with Image.open(path) as im:
                im = im.convert("RGB")
                w, h = im.size
                if not args.no_thumbs:
                    art.write_thumbnail(out_dir, i, im)
        except (OSError, ValueError):
            w = h = 0
        rel = os.path.relpath(path, data_dir).replace("\\", "/")
        rows.append({
            "id": i,
            "rel_path": rel,
            "dhash": dhash_by_id.get(i) or "",
            "cluster_id": cluster_of.get(i, -1),
            "pixels": int(w * h),
            "width": int(w),
            "height": int(h),
            "is_original": CFG.ORIGINAL_DIR_NAME in rel.lower().split("/"),
            "thumb_file": f"thumbnails/{i}.jpg",
        })

    calibration = {
        "optimal_threshold": best_t,
        "f1": best_f1,
        "precision": next(r["precision"] for r in history if r["threshold"] == best_t),
        "recall": next(r["recall"] for r in history if r["threshold"] == best_t),
        "objective": CFG.CALIBRATION_OBJECTIVE,
        "n_ground_truth_pairs": len(gt),
        "history": history,
    }

    manifest = art.save_bundle(out_dir, index, rows, calibration, thumbnails=None)
    print(f"\nBundle written to {out_dir}")
    print(json.dumps(manifest, indent=2))
    print(f"Clusters: {len(clusters)} | duplicate images: "
          f"{sum(len(c['duplicates']) for c in clusters)}")


def recalibrate(args):
    """Recompute calibration from an existing bundle (no re-embedding)."""
    bundle_dir = args.artifacts
    index = faiss.read_index(os.path.join(bundle_dir, "index.faiss"))
    import pandas as pd
    meta = pd.read_parquet(os.path.join(bundle_dir, "metadata.parquet"))
    ids = [str(x) for x in meta["id"].tolist()]
    id_to_path = dict(zip(ids, meta["rel_path"].tolist()))

    min_t = min(CFG.CALIBRATION_THRESHOLDS)
    pairs = find_semantic_pairs(index, ids, threshold=min_t, top_k=args.top_k)
    gt = _ground_truth_for_ids(ids, id_to_path)
    best_t, best_f1, history = calibrate(pairs, gt)
    print(f"Optimal threshold={best_t:.2f}  F1={best_f1:.4f}")

    calib_path = os.path.join(bundle_dir, "calibration.json")
    with open(calib_path, "w") as f:
        json.dump({
            "optimal_threshold": best_t, "f1": best_f1,
            "precision": next(r["precision"] for r in history if r["threshold"] == best_t),
            "recall": next(r["recall"] for r in history if r["threshold"] == best_t),
            "objective": CFG.CALIBRATION_OBJECTIVE,
            "n_ground_truth_pairs": len(gt), "history": history,
        }, f, indent=2)
    print(f"Updated {calib_path}")


def main():
    p = argparse.ArgumentParser(description="Mirror of Maya offline indexer")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="build an artifact bundle from a dataset")
    b.add_argument("--data", required=True)
    b.add_argument("--out", default=CFG.ARTIFACT_DIR)
    b.add_argument("--model", default=CFG.MODEL_ID)
    b.add_argument("--pooling", default=CFG.POOLING, choices=["cls", "mean"])
    b.add_argument("--top-k", type=int, default=50)
    b.add_argument("--no-thumbs", action="store_true")
    b.set_defaults(func=build)

    c = sub.add_parser("calibrate", help="recalibrate an existing bundle")
    c.add_argument("--artifacts", default=CFG.ARTIFACT_DIR)
    c.add_argument("--top-k", type=int, default=50)
    c.set_defaults(func=recalibrate)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
