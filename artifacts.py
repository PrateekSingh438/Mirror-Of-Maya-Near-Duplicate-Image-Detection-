"""Portable artifact bundle: save (indexer) and load (serving app).

The bundle makes the deployed app self-contained: it ships thumbnails so
results render without the original images, and a manifest so the app can
refuse a bundle that was built with a different model.

Layout:
    artifacts/
      index.faiss          FAISS index of normalized vectors
      metadata.parquet     one row per image (id, rel_path, dhash, cluster_id,
                           pixels, width, height, is_original, thumb_file)
      thumbnails/          small JPEGs keyed by id
      calibration.json     {optimal_threshold, f1, precision, recall, history}
      manifest.json        {model_id, embedding_dim, pooling, faiss_type,
                           n_images, created_at, lib_versions}
"""

import json
import os
import shutil
import zipfile
from datetime import datetime, timezone

import faiss
import pandas as pd
from PIL import Image

from config import CFG


# --------------------------------------------------------------------------- #
# Save (offline indexer)
# --------------------------------------------------------------------------- #
def write_thumbnail(out_dir, img_id, image):
    """Downsize and save a single thumbnail JPEG into the bundle."""
    thumb_dir = os.path.join(out_dir, "thumbnails")
    os.makedirs(thumb_dir, exist_ok=True)
    thumb = image.convert("RGB").copy()
    thumb.thumbnail((CFG.THUMBNAIL_SIZE, CFG.THUMBNAIL_SIZE))
    thumb.save(os.path.join(thumb_dir, f"{img_id}.jpg"), "JPEG", quality=82)


def pack_thumbnails(out_dir):
    """Zip out_dir/thumbnails/*.jpg into out_dir/thumbnails.zip and drop the dir.

    Keeps the bundle to a handful of files so it uploads/downloads as a unit.
    """
    thumb_dir = os.path.join(out_dir, "thumbnails")
    if not os.path.isdir(thumb_dir):
        return None
    zip_path = os.path.join(out_dir, "thumbnails.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as zf:
        for name in sorted(os.listdir(thumb_dir)):
            zf.write(os.path.join(thumb_dir, name), name)
    shutil.rmtree(thumb_dir)
    return zip_path


def _extract_thumbnails(zip_path):
    """Extract thumbnails.zip once into a stable temp dir; return that dir."""
    import hashlib
    key = hashlib.md5(os.path.abspath(zip_path).encode()).hexdigest()[:12]
    dest = os.path.join(CFG.TEMP_DIR, "thumbs", key)
    marker = os.path.join(dest, ".done")
    if os.path.isfile(marker):
        return dest
    os.makedirs(dest, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest)
    open(marker, "w").close()
    return dest


def save_bundle(out_dir, index, metadata_rows, calibration, thumbnails=None):
    """Write a bundle to `out_dir`.

    metadata_rows: list of dicts (must include 'id', 'thumb_file').
    thumbnails: optional dict id -> PIL.Image. If None, thumbnails are assumed
    to have been streamed in already via write_thumbnail().
    """
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(os.path.join(out_dir, "thumbnails"), exist_ok=True)

    faiss.write_index(index, os.path.join(out_dir, "index.faiss"))

    df = pd.DataFrame(metadata_rows)
    df.to_parquet(os.path.join(out_dir, "metadata.parquet"), index=False)

    for img_id, img in (thumbnails or {}).items():
        write_thumbnail(out_dir, img_id, img)

    # Pack thumbnails into a single zip — thousands of tiny files would blow
    # past the Hub's request rate limit and make app cold-start slow.
    pack_thumbnails(out_dir)

    with open(os.path.join(out_dir, "calibration.json"), "w") as f:
        json.dump(calibration, f, indent=2)

    import faiss as _f
    import torch
    import transformers
    manifest = {
        "model_id": CFG.MODEL_ID,
        "pooling": CFG.POOLING,
        "embedding_dim": index.d,
        "faiss_type": type(index).__name__,
        "n_images": int(index.ntotal),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "lib_versions": {
            "faiss": getattr(_f, "__version__", "unknown"),
            "torch": torch.__version__,
            "transformers": transformers.__version__,
        },
    }
    with open(os.path.join(out_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest


# --------------------------------------------------------------------------- #
# Load (serving app)
# --------------------------------------------------------------------------- #
def _resolve(cfg):
    """Return a local directory for the bundle, fetching/caching if remote.

    None means no bundle is available -> the app runs in Mode B only.
    """
    src = cfg.ARTIFACT_SOURCE
    if src == "local":
        return cfg.ARTIFACT_DIR if _looks_like_bundle(cfg.ARTIFACT_DIR) else None
    if src == "hf":
        if not cfg.HF_ARTIFACT_REPO:
            return None
        try:
            from huggingface_hub import snapshot_download
            return snapshot_download(repo_id=cfg.HF_ARTIFACT_REPO,
                                     repo_type="dataset")
        except Exception:
            return None
    if src == "url":
        return _download_zip(cfg.ARTIFACT_URL) if cfg.ARTIFACT_URL else None
    return None


def _looks_like_bundle(path):
    return bool(path) and os.path.isfile(os.path.join(path, "manifest.json"))


def _download_zip(url):
    import requests
    cache_dir = os.path.join(CFG.TEMP_DIR, "artifact_bundle")
    if _looks_like_bundle(cache_dir):
        return cache_dir
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
    os.makedirs(cache_dir, exist_ok=True)
    zip_path = os.path.join(CFG.TEMP_DIR, "bundle.zip")
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(zip_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(cache_dir)
    os.remove(zip_path)
    # Allow a single top-level folder inside the zip.
    if not _looks_like_bundle(cache_dir):
        entries = [os.path.join(cache_dir, e) for e in os.listdir(cache_dir)]
        for e in entries:
            if _looks_like_bundle(e):
                return e
    return cache_dir


def load_bundle(cfg=CFG):
    """Load a bundle, or return None to signal Mode B only."""
    path = _resolve(cfg)
    if not _looks_like_bundle(path):
        return None

    with open(os.path.join(path, "manifest.json")) as f:
        manifest = json.load(f)
    if manifest.get("model_id") != cfg.MODEL_ID:
        raise ValueError(
            f"Bundle model '{manifest.get('model_id')}' != configured "
            f"MODEL_ID '{cfg.MODEL_ID}'. Rebuild the bundle or change MODEL_ID."
        )

    calib_path = os.path.join(path, "calibration.json")
    calib = {}
    if os.path.isfile(calib_path):
        with open(calib_path) as f:
            calib = json.load(f)

    # Thumbnails ship as a single zip (preferred) or a loose folder (legacy).
    thumbs_dir = os.path.join(path, "thumbnails")
    zip_path = os.path.join(path, "thumbnails.zip")
    if not os.path.isdir(thumbs_dir) and os.path.isfile(zip_path):
        thumbs_dir = _extract_thumbnails(zip_path)

    return {
        "dir": path,
        "index": faiss.read_index(os.path.join(path, "index.faiss")),
        "meta": pd.read_parquet(os.path.join(path, "metadata.parquet")),
        "calibration": calib,
        "thumbnails": thumbs_dir,
        "manifest": manifest,
    }


def thumb_path(bundle, img_id):
    p = os.path.join(bundle["thumbnails"], f"{img_id}.jpg")
    return p if os.path.isfile(p) else None
