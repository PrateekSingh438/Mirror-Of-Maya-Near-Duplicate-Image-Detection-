## Mirror of Maya: Robust Near-Duplicate Image Detection
Mirror of Maya is a production-grade Near-Duplicate Image Detection (NDID) pipeline designed to identify and cluster visually similar images, even under severe degradation such as heavy compression, blurring, and noise.
Powered by Meta's DINOv2 (Self-Supervised Vision Transformer) and enhanced with a custom Test-Time Augmentation (TTA) engine, this system outperforms traditional hashing and CLIP-based methods, achieving an F1 score of 0.80+ on extreme test cases (JPEG Quality 3) where standard models fail.

## Key Features
 AI-Powered Detection: Leverages DINOv2 embeddings to capture global object geometry rather than relying on brittle pixel-level details.

 Robust TTA Engine: Implements Test-Time Augmentation (Gaussian Blur, Grayscale, Horizontal Flip) to "see through" artifacts and pixelation.

Galaxy Cluster Visualization: Interactive PCA-based projection to visualize the high-dimensional embedding space and identify duplicate clusters intuitively.

Asymmetric Search Strategy: Maintains a "Sharp" database index while querying with "Robust" embeddings. This maximizes recall for distorted queries without polluting the reference database.

Action Queue: A streamlined cluster review system to efficiently clean datasets and reclaim storage space.

Automatic Benchmarking: Built-in evaluation tools to calculate Precision, Recall, and F1 scores against ground truth (Copydays dataset compatible).

## Technical Architecture: Why DINOv2?
Traditional methods rely on cryptographic hashing (MD5/SHA) or perceptual hashing (pHash), which fail immediately upon rotation or compression. While CLIP (OpenAI) is the standard for image retrieval, our benchmarking revealed critical limitations for duplicate detection.

| Feature                     | CLIP (OpenAI)                | DINOv2 (Meta)                          | The "Mirror of Maya" Advantage |
|----------------------------|------------------------------|----------------------------------------|--------------------------------|
| Training Objective         | Text-Image Alignment         | Self-Supervised Learning (SSL)         | DINOv2 learns object structure without text labels, making it superior for visual similarity |
| Texture Bias               | High                         | Low (Shape-biased)                     | Our implementation exploits DINOv2's shape bias to ignore JPEG artifacts |
| Local Features             | Weak                         | Strong                                 | Can match cropped or partially occluded images significantly better |
| Resolution Handling        | Fixed (224x224)             | Flexible (Patch-based)                 | Handles varying aspect ratios naturally |


## Methodology & Innovation

### 1. Asymmetric Search Engine

Unlike standard pipelines that use the same embedding logic for both indexing and querying, we developed an **Asymmetric approach** to handle noise:

**Indexing (The "Gallery")**
- Images are processed using the **Standard DINOv2 pipeline**
- We preserve high-frequency details to maintain a **Perfect Reference**

**Querying (The "Probe")**
Queries undergo **Test-Time Augmentation (TTA):**

- **View 1:** Original Image  
- **View 2:** Gaussian Blur (kernel 5x5) → Removes 8x8 JPEG grid blocks  
- **View 3:** Grayscale → Removes chroma noise  

**Fusion Strategy**
- The three embeddings are averaged to create a **Robust Vector**  
- This vector matches reliably against the clean gallery image

---

### 2. The "Small Model" Advantage (Shape vs. Texture)

During development we discovered a critical insight:

> **DINOv2-Small (21M params) outperformed DINOv2-Base (86M params) for near-duplicate detection**

#### Why this happens

- The **Base model has higher Texture Bias**  
  - It interprets JPEG artifacts as new textures  
  - This reduces similarity scores for heavily compressed images  

- The **Small model exhibits stronger Shape Bias**  
  - Limited capacity forces it to focus on global structure  
  - It effectively ignores pixel-level noise  
  - Matches based on object silhouette rather than compression artifacts  

#### Practical Outcome

- More stable matching under:
  - JPEG quality 3–10  
  - strong compression  
  - color distortions  
- Better recall without lowering similarity threshold


inria working dataset link http://web.archive.org/web/20160414091603/https://lear.inrialpes.fr/~jegou/data.php



