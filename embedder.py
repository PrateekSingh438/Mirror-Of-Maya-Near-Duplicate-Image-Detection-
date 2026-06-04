"""Shared DINOv2 embedding extraction.

Imported by BOTH the offline indexer and the serving app so that vectors
produced offline and online are byte-for-byte comparable. Output vectors are
always L2-normalized float32, so cosine similarity == inner product (FAISS IP).
"""

from functools import lru_cache

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from transformers import AutoImageProcessor, AutoModel

from config import CFG


@lru_cache(maxsize=2)
def _load(model_id):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    processor = AutoImageProcessor.from_pretrained(model_id)
    model = AutoModel.from_pretrained(model_id).eval().to(device)
    return processor, model, device


def get_device():
    return _load(CFG.MODEL_ID)[2]


def embedding_dim(model_id=None):
    _, model, _ = _load(model_id or CFG.MODEL_ID)
    return int(model.config.hidden_size)


def _pool(last_hidden_state, pooling):
    # last_hidden_state: [B, 1 + num_patches, D]; index 0 is the CLS token.
    if pooling == "mean":
        return last_hidden_state[:, 1:].mean(dim=1)
    return last_hidden_state[:, 0]


@torch.inference_mode()
def embed_images(images, model_id=None, pooling=None, batch_size=None):
    """Embed a list of PIL.Image objects. Returns [N, D] L2-normalized float32."""
    if not images:
        return np.zeros((0, embedding_dim(model_id)), dtype="float32")

    model_id = model_id or CFG.MODEL_ID
    pooling = pooling or CFG.POOLING
    batch_size = batch_size or CFG.BATCH_SIZE
    processor, model, device = _load(model_id)

    out = []
    for i in range(0, len(images), batch_size):
        batch = [img.convert("RGB") for img in images[i:i + batch_size]]
        inputs = processor(images=batch, return_tensors="pt").to(device)
        hidden = model(**inputs).last_hidden_state
        vec = _pool(hidden, pooling)
        vec = F.normalize(vec, dim=-1)
        out.append(vec.cpu().numpy().astype("float32"))
    return np.vstack(out)


def embed_paths(paths, model_id=None, pooling=None, batch_size=None,
                progress=None):
    """Embed image file paths. Skips unreadable files.

    Returns (vectors [M, D] float32, kept_paths [M]) where M <= len(paths).
    """
    model_id = model_id or CFG.MODEL_ID
    pooling = pooling or CFG.POOLING
    batch_size = batch_size or CFG.BATCH_SIZE

    vectors = []
    kept = []
    buf_imgs, buf_paths = [], []

    def flush():
        if not buf_imgs:
            return
        vectors.append(embed_images(buf_imgs, model_id, pooling, batch_size))
        kept.extend(buf_paths)
        for im in buf_imgs:
            im.close()
        buf_imgs.clear()
        buf_paths.clear()

    for n, p in enumerate(paths):
        try:
            buf_imgs.append(Image.open(p).convert("RGB"))
            buf_paths.append(p)
        except (OSError, ValueError):
            continue
        if len(buf_imgs) >= batch_size:
            flush()
        if progress is not None:
            progress(n + 1)
    flush()

    if not vectors:
        return np.zeros((0, embedding_dim(model_id)), dtype="float32"), []
    return np.vstack(vectors), kept


def embed_one(image_or_path, model_id=None, pooling=None):
    """Embed a single image (path or PIL.Image). Returns [1, D] or None."""
    try:
        img = (image_or_path if isinstance(image_or_path, Image.Image)
               else Image.open(image_or_path))
        return embed_images([img], model_id, pooling, batch_size=1)
    except (OSError, ValueError):
        return None
