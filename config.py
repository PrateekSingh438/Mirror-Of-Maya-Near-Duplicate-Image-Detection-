import torch
import os

# FIX OpenMP conflict BEFORE any other imports
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# --- SYSTEM CONFIGURATION ---
PAGE_TITLE = "Mirror of Maya"
PAGE_ICON = "🔍"
LAYOUT = "wide"

# --- MODEL SETTINGS ---
# Unified model ID to prevent AttributeErrors
DEFAULT_MODEL_ID = "facebook/dinov2-base" 
MODEL_ID = DEFAULT_MODEL_ID # Alias for compatibility
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
BATCH_SIZE = 32

# --- AUTOMATIC THRESHOLD CALIBRATION ---
CALIBRATION_THRESHOLDS = [0.30, 0.40, 0.50, 0.60, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
DEFAULT_THRESHOLD = 0.75

# --- HASHING ---
HASH_SIZE = 16
HASH_THRESHOLD = 2  
USE_DHASH = True

# --- DATABASE ---
USE_IVF_INDEX = False 
INDEX_SAVE_PATH = "./indexes"
ENABLE_INCREMENTAL_INDEXING = True

# --- FILE HANDLING ---
SUPPORTED_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.webp', '.tiff')

# CHANGE THIS PATH TO YOUR ACTUAL IMAGE DIRECTORY
DATASET_PATH = "./dataset_copydays" 

# FIXED: Just use 'original' folder name instead of full path
ORIGINAL_DIR_NAME = "original"

# --- UI SETTINGS ---
CLUSTERS_PER_PAGE = 10
MAX_IMAGES_PER_ROW = 3
TEMP_QUERY_FILE = "temp_query.jpg"

# --- ADVANCED FEATURES ---
ENABLE_QUALITY_METRICS = True
USE_DBSCAN_CLUSTERING = True   
ENABLE_ADVANCED_TTA = False    

# Quality metric weights
SHARPNESS_WEIGHT = 0.40
ENTROPY_WEIGHT = 0.30
RESOLUTION_WEIGHT = 0.20
BLOCKINESS_PENALTY = 0.10

# DBSCAN parameters
DBSCAN_EPS = 0.15
DBSCAN_MIN_SAMPLES = 2

# --- STORAGE LIMITS ---
MAX_DELETION_QUEUE_SIZE = 1000

# --- NUMERICAL STABILITY ---
EPSILON = 1e-9

# --- CLUSTERING MODE ---
# "basename": Only cluster images with same filename (conservative, like query tab)
# "semantic": Cluster all similar images regardless of filename (may include false positives)
CLUSTERING_MODE = "basename"  # or "semantic"