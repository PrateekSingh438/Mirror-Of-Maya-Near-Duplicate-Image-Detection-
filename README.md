# Mirror of Maya — Near-Duplicate Image Detection

Near-duplicate image detection using **DINOv2** embeddings, **FAISS** vector
search, and **dHash** perceptual hashing. Robust to JPEG compression, crops,
rotation, blur, and color shifts.

The project is split into two components so it deploys on CPU-only hosts with
**no dataset on disk**:

| Component | Runs where | Job |
|---|---|---|
| **Offline indexer** (`indexer.py`) | your machine / CI (GPU optional) | embed corpus → build FAISS index → calibrate threshold → write a portable `./artifacts` bundle |
| **Serving app** (`app.py`, Streamlit) | anywhere, CPU-only | **Mode A:** load a prebuilt bundle for search/cluster browsing · **Mode B:** dedup an uploaded batch fully in memory |

`embedder.py` and `hashing.py` are the **single source of truth**, imported by
both the indexer and the app, so offline and online produce identical vectors.

> **Why the rewrite?** The previous version indexed a hardcoded local folder at
> runtime, so it was useless when deployed (the host has no dataset, an ephemeral
> filesystem, and no GPU). Mode B now guarantees the deployed app always works,
> and Mode A serves a prebuilt corpus without ever touching a local dataset path.

## Pipeline

```
Images
  ├─ Stage 0  dHash fast-pass        exact / near-exact (Hamming ≤ 2)
  └─ Stage 1  DINOv2 embeddings      L2-normalized → FAISS IndexFlatIP (cosine)
                  ↓
            threshold filter  (F1-calibrated against ground truth)
                  ↓
            NetworkX connected-components clustering
```

- **Embedding:** DINOv2 CLS token (or mean-pooled patches via `POOLING=mean`),
  L2-normalized so inner product == cosine similarity.
- **Index:** FAISS `IndexFlatIP` (exact). Normalized vectors throughout.
- **Calibration:** sweep thresholds, compute precision/recall/F1 against
  ground-truth pairs, pick the F1-optimal threshold (or hit a target
  precision/recall via `CALIBRATION_OBJECTIVE`).
- **Ground truth** is derived from the dataset's known structure (COPYDAYS encodes
  the source image in the filename), not from the detector — so it is a real
  label, not circular.

## Quick start (local)

```bash
python -m venv venv && venv\Scripts\activate     # Windows
pip install -r requirements.txt

# 1) Build a portable bundle from a dataset (GPU optional)
python -m indexer build --data ./dataset_copydays --out ./artifacts

# 2) Run the app (Mode A loads ./artifacts; Mode B always works)
streamlit run app.py
```

The app runs **with no dataset present** — it loads a bundle from the configured
source, or falls back to stateless Mode B.

## App tabs

- **Upload & Dedup** *(Mode B, always on)* — drop images or a `.zip`; they're
  embedded + clustered in memory, with a one-click "download deduped set".
- **Search** *(Mode A)* — query-by-image against the prebuilt corpus.
- **Clusters** *(Mode A)* — browse precomputed duplicate clusters (renders from
  bundled thumbnails; originals not required).
- **Versus** *(always on)* — direct two-image cosine + dHash comparison.
- **Analytics** — the calibration PR curve (Mode A) or session score histogram (Mode B).
- **Architecture** — pipeline + loaded-bundle stats.

## Deployment (CPU, no GPU)

The deployed app never references a local dataset path. Ship the bundle to remote
storage and point the app at it via secrets/env:

**Streamlit Community Cloud**
1. `python -m indexer build --data ./dataset_copydays --out ./artifacts`
2. Push the bundle to a Hugging Face **dataset** repo:
   `huggingface-cli upload <user>/mirror-of-maya-index ./artifacts --repo-type dataset`
3. In the app's **Secrets**, set:
   ```toml
   ARTIFACT_SOURCE = "hf"
   HF_ARTIFACT_REPO = "<user>/mirror-of-maya-index"
   MODEL_ID = "facebook/dinov2-small"
   ```
4. The app downloads + caches the bundle at boot. Use `dinov2-small` for fast CPU
   inference. With no secrets set, it still runs in Mode B.

See [.streamlit/secrets.toml.example](.streamlit/secrets.toml.example). `ARTIFACT_SOURCE`
also supports `"url"` (a public `.zip`) and `"local"` (a committed `./artifacts`).

**Docker / self-host:** `docker build -t mirror-of-maya . && docker run -p 8501:8501 mirror-of-maya`
(bake `./artifacts` in, or set `ARTIFACT_SOURCE=hf`). Swap in CUDA torch wheels for GPU.

## Configuration

All settings read from env vars / `st.secrets` with sane defaults
([config.py](config.py)). Key ones:

| Key | Default | Notes |
|---|---|---|
| `MODEL_ID` | `facebook/dinov2-small` | `small` \| `base` \| `large` |
| `POOLING` | `cls` | `cls` \| `mean` (mean is more crop-robust) |
| `CALIBRATION_OBJECTIVE` | `f1` | `f1` \| `target_precision` \| `target_recall` |
| `ARTIFACT_SOURCE` | `local` | `local` \| `hf` \| `url` |
| `HF_ARTIFACT_REPO` | — | HF dataset repo holding `./artifacts` |

## Benchmarks

Regenerated from a real `indexer build` run — `facebook/dinov2-small` (CLS
pooling, 384-d), FAISS `IndexFlatIP`, on **2,826** COPYDAYS images (157 source
identities). Evaluation is **strict pairwise**: ground truth is *every* pair of
images sharing a source identity (**24,021** positive pairs), so hard cross-attack
pairs (e.g. heavy JPEG vs heavy crop) must both clear the threshold to count.

| Threshold | Precision | Recall | F1 | Pairs detected |
|---:|---:|---:|---:|---:|
| 0.30 | 0.322 | **0.921** | 0.477 | 68,679 |
| 0.50 | 0.590 | 0.838 | 0.692 | 34,142 |
| **0.60** | **0.765** | **0.761** | **0.763** | 23,895 |
| 0.70 | 0.886 | 0.650 | 0.750 | 17,644 |
| 0.75 | 0.925 | 0.583 | 0.715 | 15,132 |
| 0.90 | 0.993 | 0.265 | 0.418 | 6,402 |
| 0.95 | **1.000** | 0.115 | 0.207 | 2,769 |

**F1-optimal threshold = 0.60** → F1 **0.763**, precision 0.765, recall 0.761.
The point of calibration is the *curve*, not one number: the same index serves a
high-recall operating point (~0.92 recall at 0.30) or a high-precision one
(>0.99 precision at 0.90+), selected via `CALIBRATION_OBJECTIVE`.

> The earlier README claimed F1 > 0.93; that figure did not come from this
> pipeline's own evaluation. These numbers are reproducible from the bundle's
> `calibration.json`.

## Artifact bundle format

```
artifacts/
├── index.faiss          FAISS index (normalized vectors)
├── metadata.parquet     id, rel_path, dhash, cluster_id, pixels, w, h, is_original, thumb_file
├── thumbnails/          small JPEGs keyed by id (so the app needs no originals)
├── calibration.json     {optimal_threshold, f1, precision, recall, history:[...]}
└── manifest.json        {model_id, embedding_dim, pooling, faiss_type, n_images, ...}
```

The app refuses a bundle whose `manifest.model_id` differs from the configured `MODEL_ID`.

## Project layout

```
app.py            Streamlit shell: mode switch + tabs
config.py         CFG — all settings from env / st.secrets
embedder.py       DINOv2 embedding (SHARED by indexer + app)
hashing.py        dHash + Hamming (SHARED)
dedup.py          ground truth, candidate pairs, calibration, clustering, metrics
search.py         query-by-image + two-image comparison
stateless.py      Mode B: in-memory batch dedup
artifacts.py      bundle save/load + remote fetch (local/HF/URL) + manifest check
indexer.py        offline CLI: `build`, `calibrate`
ui/               components.py · session.py · tabs.py
.streamlit/       config.toml · secrets.toml.example
Dockerfile        optional self-host
```

## Datasets

- INRIA COPYDAYS: http://web.archive.org/web/20160414091603/https://lear.inrialpes.fr/~jegou/data.php

```
dataset_copydays/
├── original/        source images
├── jpeg/{3,5,...}   JPEG compression attacks
└── crops/...        crop attacks
```

## Acknowledgments

DINOv2 (Meta AI) · FAISS (Meta) · imagehash · Streamlit · INRIA COPYDAYS.
