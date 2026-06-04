"""dHash perceptual hashing + Hamming utilities.

Shared by indexer and app. The dHash stage is the cheap fast-pass that removes
exact / near-exact duplicates before any embedding work.
"""

import imagehash
from PIL import Image

from config import CFG


def compute_dhash(image_or_path, hash_size=None):
    """Return the dHash hex string for an image, or None if unreadable."""
    hash_size = hash_size or CFG.HASH_SIZE
    try:
        img = (image_or_path if isinstance(image_or_path, Image.Image)
               else Image.open(image_or_path).convert("RGB"))
        return str(imagehash.dhash(img, hash_size=hash_size))
    except (OSError, ValueError):
        return None


def hamming(hex_a, hex_b):
    """Hamming distance between two dHash hex strings."""
    return imagehash.hex_to_hash(hex_a) - imagehash.hex_to_hash(hex_b)


def find_hash_duplicates(hashes, threshold=None):
    """Group items by near-identical dHash.

    `hashes` is a list of (id, hex) pairs. Returns a list of duplicate pairs
    [{"a": id, "b": id, "distance": d}] for items within `threshold` bits.
    Uses a 4-hex-char prefix bucket to avoid an O(n^2) sweep on large sets.
    """
    threshold = threshold if threshold is not None else CFG.HASH_THRESHOLD
    buckets = {}
    pairs = []
    for item_id, hx in hashes:
        if not hx:
            continue
        key = hx[:4]
        bucket = buckets.setdefault(key, [])
        matched = False
        for prev_id, prev_hx in bucket:
            dist = hamming(hx, prev_hx)
            if dist <= threshold:
                pairs.append({"a": prev_id, "b": item_id, "distance": int(dist)})
                matched = True
                break
        if not matched:
            bucket.append((item_id, hx))
    return pairs
