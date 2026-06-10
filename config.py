import os
import tempfile

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# System
PAGE_TITLE = "Mirror of Maya"
LAYOUT = "wide"

# Model
DEFAULT_MODEL_ID = "facebook/dinov2-small"
BATCH_SIZE = 16  # images per forward pass

# Perceptual hashing (exact / near-exact duplicates)
HASH_SIZE = 16          # 16x16 dHash -> 256 bits
HASH_THRESHOLD = 2      # max Hamming distance to call two images exact copies

# Similarity thresholds (cosine on L2-normalized CLS embeddings)
SCAN_THRESHOLD_FLOOR = 0.40   # candidate pairs are collected above this once per scan
DEFAULT_THRESHOLD = 0.75
MIN_THRESHOLD = 0.40
MAX_THRESHOLD = 0.99

# Calibration (only runs when the dataset provides ground truth)
CALIBRATION_SWEEP_START = 0.40
CALIBRATION_SWEEP_STOP = 0.99
CALIBRATION_SWEEP_STEP = 0.01
CALIBRATION_HOLDOUT_FRACTION = 0.5
CALIBRATION_SEED = 42

# Files
SUPPORTED_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.webp', '.tiff')
DATASET_PATH = os.environ.get("MAYA_DATASET_PATH", "./dataset_copydays")
TRASH_DIR_NAME = ".maya_trash"  # soft-deleted files are moved here, never os.remove'd

# UI
CLUSTERS_PER_PAGE = 5
THUMBNAIL_MAX_SIZE = 384  # px, longest side

# Temp directory for uploaded/query files
TEMP_DIR = os.path.join(tempfile.gettempdir(), "mirror_of_maya")
os.makedirs(TEMP_DIR, exist_ok=True)
THUMBS_DIR = os.path.join(TEMP_DIR, "thumbs")
os.makedirs(THUMBS_DIR, exist_ok=True)
