import torch

# Dataset Configuration
DATASET_PATH = "./dataset_copydays"
ORIGINAL_DIR_NAME = "original"

# Model Configuration
MODEL_ID = "facebook/dinov2-small"
MODEL_OPTIONS = {
    "Small": "facebook/dinov2-small",
    "Base": "facebook/dinov2-base",
    "Large": "facebook/dinov2-large"
}

# Device Configuration
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
BATCH_SIZE = 32

# Similarity Thresholds
SIMILARITY_THRESHOLD = 0.85
DEFAULT_THRESHOLD_PERCENT = 85
BENCHMARK_THRESHOLD = 0.80

# Hash Configuration
HASH_SIZE = 16
HASH_THRESHOLD = 0

# Image Extensions
SUPPORTED_IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp')

# UI Configuration
PAGE_TITLE = "Mirror of Maya"
PAGE_ICON = "🔍"
LAYOUT = "wide"

# Pagination
CLUSTERS_PER_PAGE = 5
MAX_IMAGES_PER_ROW = 5

# Visualization
MAX_GALAXY_PLOT_IMAGES = 5000
GALAXY_COLOR = "#00CC96"

# Search Configuration
MAX_SEARCH_RESULTS = 50

# File Paths
TEMP_QUERY_FILE = "temp_query.jpg"

# Environment Variables
ENV_KMP_DUPLICATE_LIB = "TRUE"

# Size Conversion
BYTES_TO_MB = 1024 * 1024

# Benchmark Attack Categories
ATTACK_CATEGORIES = {
    "JPEG 3": "jpeg/3",
    "JPEG 5": "jpeg/5",
    "JPEG 8": "jpeg/8",
    "JPEG 10": "jpeg/10",
    "JPEG 15": "jpeg/15",
    "JPEG 20": "jpeg/20",
    "JPEG 30": "jpeg/30",
    "JPEG 50": "jpeg/50",
    "JPEG 75": "jpeg/75",
    "Strong": "strong",
}

# Benchmark Thresholds
EXCELLENT_RECALL_THRESHOLD = 0.9
WEAK_RECALL_THRESHOLD = 0.5

# Image Processing
GAUSSIAN_BLUR_KERNEL = (5, 5)
GAUSSIAN_BLUR_SIGMA = 0

# Metrics
EPSILON = 1e-9