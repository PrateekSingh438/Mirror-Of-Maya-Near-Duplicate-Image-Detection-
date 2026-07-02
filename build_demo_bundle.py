"""Build the demo bundle that lets the deployed app start with results.

Run locally where the copydays dataset lives:

    python build_demo_bundle.py

Writes:
    demo_bundle/embeddings.npy   precomputed DINOv2 embeddings
    demo_bundle/hash_bits.npy    packed dHash fingerprints
    demo_bundle/files.json       relative paths, same order as the embeddings
    demo_bundle/eval.json        calibrated threshold + held-out metrics + sweep
    demo_bundle/thumbs.zip       256px thumbnails preserving the folder tree
    demo_samples/                a few one-click query images for the Search tab

The app (ui_components.maybe_load_demo) loads this at startup so visitors see
a working duplicate index immediately instead of an empty screen.
"""
import io
import json
import os
import shutil
import time
import zipfile

import numpy as np
from PIL import Image

import config
from engine import DuplicateDetector
from utils import generate_ground_truth

DATASET = config.DATASET_PATH
BUNDLE_DIR = "./demo_bundle"
SAMPLES_DIR = "./demo_samples"
THUMB_SIZE = 256
THUMB_QUALITY = 80


def main():
    if not os.path.isdir(DATASET):
        raise SystemExit(f"Dataset not found: {DATASET}")

    print(f"Indexing {DATASET} with {config.DEFAULT_MODEL_ID}...")
    t0 = time.time()
    det = DuplicateDetector(config.DEFAULT_MODEL_ID)
    det.bulk_index(DATASET)
    print(f"Indexed {det.index.ntotal} images in {time.time() - t0:.0f}s")

    print("Calibrating threshold...")
    groups, gt_pairs = generate_ground_truth(DATASET)
    result = det.calibrate_threshold(groups, gt_pairs)
    if result is None:
        raise SystemExit("Dataset has no ground truth; cannot calibrate.")
    print(f"Threshold {result['threshold']:.2f}, "
          f"held-out F1 {result['holdout']['f1']:.3f}")

    if os.path.exists(BUNDLE_DIR):
        shutil.rmtree(BUNDLE_DIR)
    os.makedirs(BUNDLE_DIR)

    rel_files = [os.path.relpath(f, DATASET).replace(os.sep, "/")
                 for f in det.stored_files]

    np.save(os.path.join(BUNDLE_DIR, "embeddings.npy"), det.embeddings)
    np.save(os.path.join(BUNDLE_DIR, "hash_bits.npy"), det.hash_bits)
    with open(os.path.join(BUNDLE_DIR, "files.json"), "w") as f:
        json.dump(rel_files, f)
    with open(os.path.join(BUNDLE_DIR, "eval.json"), "w") as f:
        json.dump(result, f)

    print(f"Writing {len(rel_files)} thumbnails into thumbs.zip...")
    zip_path = os.path.join(BUNDLE_DIR, "thumbs.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as zf:
        for src, rel in zip(det.stored_files, rel_files):
            with Image.open(src) as im:
                thumb = im.convert("RGB")
                thumb.thumbnail((THUMB_SIZE, THUMB_SIZE))
            buf = io.BytesIO()
            thumb.save(buf, format="JPEG", quality=THUMB_QUALITY)
            zf.writestr(rel, buf.getvalue())
    print(f"thumbs.zip: {os.path.getsize(zip_path) / 1e6:.1f} MB")

    _write_samples(det)
    print("Demo bundle complete.")


def _write_samples(det):
    """Three one-click query images for the Search tab: a heavy crop and a
    low quality JPEG (both match the corpus) plus one unrelated photo."""
    os.makedirs(SAMPLES_DIR, exist_ok=True)
    for f in os.listdir(SAMPLES_DIR):
        os.remove(os.path.join(SAMPLES_DIR, f))

    def save_sample(src, name):
        with Image.open(src) as im:
            thumb = im.convert("RGB")
            thumb.thumbnail((THUMB_SIZE, THUMB_SIZE))
            thumb.save(os.path.join(SAMPLES_DIR, name), quality=THUMB_QUALITY)
        print(f"  sample: {name} <- {src}")

    crop = next((f for f in det.stored_files if "crop_10_percent" in f), None)
    jpeg3 = next((f for f in det.stored_files
                  if f.replace("\\", "/").find("jpeg/3/") != -1), None)
    if crop:
        save_sample(crop, "1_heavily_cropped_copy.jpg")
    if jpeg3:
        save_sample(jpeg3, "2_low_quality_jpeg_copy.jpg")

    # an image that is NOT in the demo corpus, to show a no-match result
    unrelated_dir = "./dataset"
    if os.path.isdir(unrelated_dir):
        unrelated = next(
            (os.path.join(unrelated_dir, f) for f in sorted(os.listdir(unrelated_dir))
             if f.lower().endswith(('.jpg', '.jpeg', '.png'))), None)
        if unrelated:
            save_sample(unrelated, "3_unrelated_photo.jpg")


if __name__ == "__main__":
    main()
