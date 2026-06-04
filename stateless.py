"""Mode B — stateless, in-session deduplication of an uploaded batch.

Nothing is persisted. This path has no dataset dependency at all, so it
guarantees the deployed app is never useless even with no prebuilt bundle.

Pairs are generated once at the lowest calibration threshold and returned in
full, so the UI can re-cluster at any slider value without re-embedding.
"""

import faiss

from config import CFG
from dedup import find_semantic_pairs
from embedder import embed_images, embedding_dim
from hashing import compute_dhash, find_hash_duplicates


def dedup_batch(items, top_k=20, progress=None):
    """Embed and pair an uploaded batch.

    `items` is a list of (label, PIL.Image). Returns
    {pairs, meta, n_images} where pairs are at the lowest calibration
    threshold and meta maps label -> {pixels} for canonical-original selection.
    """
    items = [(label, img) for label, img in items if img is not None]
    if not items:
        return {"pairs": [], "meta": {}, "n_images": 0}

    labels = [label for label, _ in items]
    images = [img.convert("RGB") for _, img in items]

    if progress:
        progress("Hashing...")
    hashes = [(labels[i], compute_dhash(images[i])) for i in range(len(images))]
    hash_pairs = find_hash_duplicates(hashes)

    if progress:
        progress("Embedding...")
    vectors = embed_images(images)
    dim = vectors.shape[1] if vectors.size else embedding_dim()
    index = faiss.IndexFlatIP(dim)
    if vectors.size:
        index.add(vectors)

    if progress:
        progress("Matching...")
    pairs = find_semantic_pairs(index, labels, threshold=min(CFG.CALIBRATION_THRESHOLDS),
                                top_k=top_k, hash_pairs=hash_pairs)

    meta = {labels[i]: {"pixels": images[i].size[0] * images[i].size[1]}
            for i in range(len(images))}

    for im in images:
        im.close()

    return {"pairs": pairs, "meta": meta, "n_images": len(items)}
