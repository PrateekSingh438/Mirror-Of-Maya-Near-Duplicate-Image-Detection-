"""Query-by-image search and direct two-image comparison.

Works against any loaded FAISS index + parallel id list, so it serves both a
prebuilt corpus bundle (Mode A) and an in-session index (Mode B).
"""

import numpy as np

from config import CFG
from embedder import embed_one
from hashing import compute_dhash, hamming


def search_index(index, ids, query_image, threshold=None, top_k=50):
    """Return ranked matches [{id, score}] for a query image (path or PIL)."""
    threshold = CFG.DEFAULT_THRESHOLD if threshold is None else threshold
    if index is None or index.ntotal == 0:
        return []

    vec = embed_one(query_image)
    if vec is None:
        return []

    k = min(top_k, index.ntotal)
    D, I = index.search(vec, k)
    results = []
    for score, idx in zip(D[0], I[0]):
        if idx != -1 and float(score) >= threshold:
            results.append({"id": ids[int(idx)], "score": float(score)})
    return results


def compare_two(img1, img2, threshold=None):
    """Direct comparison of two images: cosine similarity + dHash distance."""
    threshold = CFG.DEFAULT_THRESHOLD if threshold is None else threshold
    v1 = embed_one(img1)
    v2 = embed_one(img2)
    if v1 is None or v2 is None:
        return None

    similarity = float(np.dot(v1[0], v2[0]))
    h1, h2 = compute_dhash(img1), compute_dhash(img2)
    hash_dist = hamming(h1, h2) if (h1 and h2) else None
    return {
        "similarity": similarity,
        "hash_distance": int(hash_dist) if hash_dist is not None else None,
        "match": similarity >= threshold,
    }
