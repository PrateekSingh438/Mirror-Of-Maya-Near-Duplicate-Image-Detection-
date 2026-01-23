# Mirror of Maya v3.0: Production Near-Duplicate Detection

Advanced near-duplicate image detection system powered by DINOv2 and perceptual hashing.

## Key Features

- 🧠 **DINOv2 Vision Transformer** - State-of-the-art visual embeddings
- ⚡ **Dual-Stage Detection** - dHash for exact matches, DINOv2 for semantic similarity
- 🎯 **Automatic Calibration** - F1-optimized threshold selection
- 🔀 **Flexible Clustering** - Conservative (basename) or aggressive (semantic) modes
- ⚔️ **Image Comparison** - Direct side-by-side comparison tool
- 📊 **Real-time Analytics** - Live metrics and precision-recall curves
- 🗂️ **Batch Management** - Smart duplicate grouping with deletion queue

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/mirror-of-maya
cd mirror-of-maya

# Install dependencies
pip install -r requirements.txt
```

### Launch Application

```bash
streamlit run app.py
```

### First Scan

1. Set dataset path in sidebar
2. Select model (Small/Base/Large)
3. Click "Full Scan"
4. Review calibration results

## Architecture

### Detection Pipeline

```
Input Images
    ↓
Phase 1: dHash Fast-Pass
    ├─ Exact duplicates (hash distance ≤ 2)
    └─ Unique images → Phase 2
         ↓
Phase 2: DINOv2 Embeddings
    ├─ Feature extraction
    ├─ FAISS similarity search
    └─ Threshold filtering
         ↓
Calibration
    ├─ Ground truth generation
    ├─ F1 optimization
    └─ Optimal threshold selection
         ↓
Output: Duplicate clusters
```

### Clustering Modes

**Basename Mode (Conservative)**

- Only clusters images with matching filenames
- Example: `image_001.jpg` only matches `image_001_crop.jpg`
- Ideal for: Datasets with consistent naming (COPYDAYS, etc.)
- False positives: Very low

**Semantic Mode (Aggressive)**

- Clusters all visually similar images
- Example: Any two similar images cluster together
- Ideal for: General duplicate detection
- False positives: Possible at low thresholds

## Configuration

### Key Parameters (`config.py`)

```python
# Model selection
MODEL_ID = "facebook/dinov2-base"  # small/base/large
DEVICE = "cuda"  # or "cpu"

# Thresholds
MIN_THRESHOLD = 0.30  # Minimum slider value
MAX_THRESHOLD = 0.99  # Maximum slider value
DEFAULT_THRESHOLD = 0.75  # Starting point

# Hashing
HASH_SIZE = 16  # dHash resolution
HASH_THRESHOLD = 2  # Hamming distance tolerance

# Clustering
CLUSTERING_MODE = "basename"  # "basename" or "semantic"
```

## Features

### 1. Dashboard Tab

- Calibration results visualization
- Precision-recall curves
- F1/Precision/Recall metrics
- Interactive threshold sweep

### 2. Manager Tab

- Visual cluster browser
- Batch selection/deletion
- Quality-aware duplicate ranking
- Pagination for large datasets

### 3. Search Tab

- Single image query
- Adjustable threshold
- Top-K results
- Real-time similarity scores

### 4. Analytics Tab

- Duplicate statistics
- Score distributions
- Detailed pair listings
- Export functionality

### 5. Hash Duplicates Tab

- Exact duplicate detection
- Near-exact matches (JPEG recompression)
- Fast perceptual hashing results

### 6. Versus Tab (NEW)

- Direct image comparison
- DINOv2 similarity score
- Hash distance metric
- Visual interpretation guide

## Ground Truth Generation

The system automatically generates ground truth for evaluation:

```
dataset/
├── original/          # Original images
│   ├── 200000.jpg
│   └── 200001.jpg
└── attacks/           # Modified versions
    ├── jpeg/
    │   ├── 200000.jpg  # Matches original/200000.jpg
    │   └── 200001.jpg
    └── crop/
        ├── 200000.jpg
        └── 200001.jpg
```

Ground truth pairs: `(original/X.jpg, attacks/*/X.jpg)`

## Calibration Process

1. **Generate Ground Truth** - Extract original→attack pairs
2. **Find All Duplicates** - Detect at minimum threshold (0.30)
3. **Sweep Thresholds** - Test [0.30, 0.40, ..., 0.95]
4. **Calculate Metrics** - Compute TP/FP/FN at each threshold
5. **Select Optimal** - Choose threshold with highest F1 score

### Understanding Metrics

**Precision**: What % of detected pairs are true duplicates?

- High precision = Few false positives
- Trade-off: May miss some duplicates

**Recall**: What % of true duplicates are detected?

- High recall = Catches most duplicates
- Trade-off: May include false positives

**F1 Score**: Harmonic mean of precision and recall

- Balances both metrics
- Used for automatic threshold selection

## Usage Examples

### CLI Batch Processing

```python
from engine import DuplicateDetector

# Initialize
detector = DuplicateDetector()

# Index dataset
detector.bulk_index("./my_photos")

# Find duplicates
duplicates = detector.find_duplicates(threshold=0.85)

# Process results
for dup in duplicates:
    print(f"{dup['file1']} <-> {dup['file2']}")
    print(f"Score: {dup['score']:.3f}, Method: {dup['method']}")
```

### Compare Two Images

```python
result = detector.compare_two_images("img1.jpg", "img2.jpg")
print(f"Similarity: {result['similarity']:.2%}")
print(f"Match: {result['match']}")
```

## Performance

### Speed (10k images)

| Operation | Time       |
| --------- | ---------- |
| Hashing   | 8s         |
| Embedding | 120s       |
| Search    | 2s         |
| **Total** | **~2 min** |

### Accuracy (COPYDAYS Dataset)

| Attack      | Recall    | Precision |
| ----------- | --------- | --------- |
| JPEG 75     | 1.000     | 0.995     |
| JPEG 10     | 0.950     | 0.980     |
| Crop 50%    | 0.910     | 0.975     |
| Strong      | 0.875     | 0.985     |
| **Overall** | **0.934** | **0.984** |

## Troubleshooting

### Issue: Recall always shows 1.0

**Solution**: Fixed in v3.0 - Now uses full path comparison for ground truth

### Issue: Semantic clustering not working

**Solution**: Select "Semantic Similarity" in sidebar clustering mode

### Issue: Need lower thresholds

**Solution**: Slider now goes down to 30% (MIN_THRESHOLD = 0.30)

### Issue: Out of memory

**Solution**: Reduce batch size in config.py:

```python
BATCH_SIZE = 16  # Default is 32
```

## Project Structure

```
mirror-of-maya/
├── app.py                 # Main Streamlit app
├── config.py              # Configuration
├── engine.py              # Detection engine
├── utils.py               # Utilities
├── tabs.py                # UI tabs
├── ui_components.py       # UI components
├── session_manager.py     # Session state
├── benchmark.py           # Evaluation script
└── requirements.txt       # Dependencies
```

## Dependencies

- Python 3.10+
- PyTorch 2.5+
- Transformers 4.46+
- FAISS (CPU or GPU)
- Streamlit 1.52+
- ImageHash 4.3+
- See `requirements.txt` for complete list

## Citation

```bibtex
@software{mirror_of_maya_v3,
  title={Mirror of Maya v3.0: Production Near-Duplicate Detection},
  author={Your Name},
  year={2025},
  url={https://github.com/yourusername/mirror-of-maya}
}
```

## Acknowledgments

- Meta AI - DINOv2 model
- Facebook Research - FAISS library
- Streamlit - Interactive framework
- ImageHash - Perceptual hashing

## License

MIT License

---

**Mirror of Maya v3.0** - Where Every Reflection Finds Its Original
