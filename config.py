import torch

# --- SYSTEM CONFIGURATION ---
PAGE_TITLE = "Mirror of Maya"
PAGE_ICON = "🔍"
LAYOUT = "wide"

# --- MODEL SETTINGS ---
MODEL_ID = "facebook/dinov2-small"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
BATCH_SIZE = 32

# --- AUTOMATIC THRESHOLD CALIBRATION ---
# The system will test these thresholds to find the best F1 score
CALIBRATION_THRESHOLDS = [0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
DEFAULT_THRESHOLD = 0.75

# --- HASHING (STRICT) ---
# Only use hashing for EXACT duplicates. Leave crops/edits to DINOv2.
HASH_SIZE = 16
HASH_THRESHOLD = 2  
USE_DHASH = True

# --- DATABASE ---
USE_IVF_INDEX = False 
INDEX_SAVE_PATH = "./indexes"
ENABLE_INCREMENTAL_INDEXING = True

# --- FILE HANDLING ---
SUPPORTED_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.webp', '.tiff')
DATASET_PATH = "./dataset_copydays"

# --- DATASET STRUCTURE ---
ORIGINAL_DIR_NAME = "original"  # Name of folder containing original images

# --- BENCHMARK CONFIGURATION ---
# Standard JPEG compression attacks
ATTACK_CATEGORIES = {
    "JPEG_3": "strong/JPEG_3",
    "JPEG_5": "strong/JPEG_5", 
    "JPEG_10": "strong/JPEG_10",
    "JPEG_75": "strong/JPEG_75",
    "Strong": "strong"
}

# Crop attack categories
CROPS_PATH = "./dataset_copydays/crops"
CROP_CATEGORIES = {
    "Crop_25%": "crop_25",
    "Crop_50%": "crop_50",
    "Crop_75%": "crop_75"
}

# Benchmark thresholds
BENCHMARK_THRESHOLD = 0.75
EXCELLENT_RECALL_THRESHOLD = 0.95
WEAK_RECALL_THRESHOLD = 0.70

# --- UI SETTINGS ---
CLUSTERS_PER_PAGE = 10
MAX_IMAGES_PER_ROW = 3
GALAXY_COLOR = "#00CC96"
TEMP_QUERY_FILE = "temp_query.jpg"

# --- ADVANCED FEATURES ---
ENABLE_QUALITY_METRICS = True  # Calculate image quality scores
USE_DBSCAN_CLUSTERING = True   # Better clustering algorithm
ENABLE_ADVANCED_TTA = False    # Enhanced test-time augmentation (slower)

# Quality metric weights
SHARPNESS_WEIGHT = 0.40
ENTROPY_WEIGHT = 0.30
RESOLUTION_WEIGHT = 0.20
BLOCKINESS_PENALTY = 0.10

# DBSCAN parameters
DBSCAN_EPS = 0.15
DBSCAN_MIN_SAMPLES = 2

# --- ENVIRONMENT ---
ENV_KMP_DUPLICATE_LIB = "TRUE"
BYTES_TO_MB = 1024 * 1024
EPSILON = 1e-9

# --- STORAGE LIMITS ---
MAX_DELETION_QUEUE_SIZE = 1000
AUTO_SAVE_INTERVAL = 300  # seconds