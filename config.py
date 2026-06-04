"""Central configuration.

Every value can be overridden by an environment variable or a Streamlit secret
so the *same* code runs locally and on a CPU-only deployment with no source edits.
Crucially, there is no hardcoded dataset path in the serving path — the deployed
app loads a prebuilt artifact bundle (Mode A) and/or dedups uploads in-memory
(Mode B). See mirror-of-maya-rebuild-spec.md.
"""

import os
import tempfile


def env(key, default=None):
    """Read a setting from os.environ first, then st.secrets, else default."""
    val = os.environ.get(key)
    if val is not None:
        return val
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return default


def _env_bool(key, default):
    val = env(key, None)
    if val is None:
        return default
    return str(val).strip().lower() in ("1", "true", "yes", "on")


def _env_int(key, default):
    try:
        return int(env(key, default))
    except (TypeError, ValueError):
        return default


class CFG:
    # --- app shell ---
    PAGE_TITLE = "Mirror of Maya"
    LAYOUT = "wide"

    # --- model / embedding ---
    MODEL_ID = env("MODEL_ID", "facebook/dinov2-small")   # small | base | large
    POOLING = env("POOLING", "cls")                       # "cls" | "mean"
    BATCH_SIZE = _env_int("BATCH_SIZE", 16)

    # --- hashing ---
    HASH_SIZE = 16
    HASH_THRESHOLD = 2

    # --- thresholds / calibration ---
    DEFAULT_THRESHOLD = 0.75
    MIN_THRESHOLD = 0.30
    MAX_THRESHOLD = 0.99
    CALIBRATION_THRESHOLDS = [0.30, 0.40, 0.50, 0.60, 0.70,
                              0.75, 0.80, 0.85, 0.90, 0.95]
    CALIBRATION_OBJECTIVE = env("CALIBRATION_OBJECTIVE", "f1")  # f1|target_precision|target_recall
    TARGET_PRECISION = float(env("TARGET_PRECISION", 0.95))
    TARGET_RECALL = float(env("TARGET_RECALL", 0.90))
    ENABLE_RERANK = _env_bool("ENABLE_RERANK", False)
    EPSILON = 1e-9

    # --- files ---
    SUPPORTED_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff")
    ORIGINAL_DIR_NAME = "original"

    # --- deployment / artifact bundle ---
    ARTIFACT_SOURCE = env("ARTIFACT_SOURCE", "local")     # local | hf | url
    ARTIFACT_DIR = env("ARTIFACT_DIR", "./artifacts")
    HF_ARTIFACT_REPO = env("HF_ARTIFACT_REPO", "")        # e.g. "user/mirror-of-maya-index"
    ARTIFACT_URL = env("ARTIFACT_URL", "")                # https URL to a .zip bundle
    THUMBNAIL_SIZE = _env_int("THUMBNAIL_SIZE", 256)

    # --- ui ---
    CLUSTERS_PER_PAGE = 5
    MAX_IMAGES_PER_ROW = 3

    # --- scratch space (always writable, ephemeral on deploy) ---
    TEMP_DIR = os.path.join(tempfile.gettempdir(), "mirror_of_maya")


os.makedirs(CFG.TEMP_DIR, exist_ok=True)
# OpenMP duplicate-lib guard for faiss + torch on some Windows/conda setups.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
