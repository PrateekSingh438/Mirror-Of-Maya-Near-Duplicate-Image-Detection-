import torch
import os
import tempfile

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# System
PAGE_TITLE = "Mirror of Maya"
LAYOUT = "wide"

# Model
DEFAULT_MODEL_ID = "facebook/dinov2-small"
MODEL_ID = DEFAULT_MODEL_ID
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
BATCH_SIZE = 32

# Thresholds
CALIBRATION_THRESHOLDS = [0.30, 0.40, 0.50, 0.60, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
DEFAULT_THRESHOLD = 0.75
MIN_THRESHOLD = 0.30  # Allow slider to go down to 30%
MAX_THRESHOLD = 0.99

# Hashing
HASH_SIZE = 16
HASH_THRESHOLD = 2
USE_DHASH = True

# Database
USE_IVF_INDEX = False
INDEX_SAVE_PATH = "./indexes"
ENABLE_INCREMENTAL_INDEXING = True

# Files
SUPPORTED_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.webp', '.tiff')
DATASET_PATH = os.environ.get("MAYA_DATASET_PATH", "./dataset_copydays")
ORIGINAL_DIR_NAME = "original"

# UI
CLUSTERS_PER_PAGE = 10
MAX_IMAGES_PER_ROW = 3

# Temp directory for uploaded/query files
TEMP_DIR = os.path.join(tempfile.gettempdir(), "mirror_of_maya")
os.makedirs(TEMP_DIR, exist_ok=True)
TEMP_QUERY_FILE = os.path.join(TEMP_DIR, "temp_query.jpg")

# Advanced
ENABLE_QUALITY_METRICS = True
USE_DBSCAN_CLUSTERING = True
ENABLE_ADVANCED_TTA = False

# Quality weights
SHARPNESS_WEIGHT = 0.40
ENTROPY_WEIGHT = 0.30
RESOLUTION_WEIGHT = 0.20
BLOCKINESS_PENALTY = 0.10

# DBSCAN
DBSCAN_EPS = 0.15
DBSCAN_MIN_SAMPLES = 2

# Limits
MAX_DELETION_QUEUE_SIZE = 1000
EPSILON = 1e-9

# Clustering
CLUSTERING_MODE = "basename"  # "basename" or "semantic"