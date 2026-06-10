import os
import random

import numpy as np
import faiss
import torch
import torch.nn.functional as F
import imagehash
from PIL import Image
from transformers import AutoImageProcessor, AutoModel

import config
from utils import walk_image_files, norm_path, pair_key, pair_metrics

# Lookup table for counting set bits in a byte (Hamming distance on packed hashes)
_POPCOUNT = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint16)


def load_backbone(model_id):
    """Load the DINOv2 processor + model once. The UI wraps this in st.cache_resource."""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    processor = AutoImageProcessor.from_pretrained(model_id)
    model = AutoModel.from_pretrained(model_id).eval().to(device)
    return processor, model, device


class DuplicateDetector:
    """Two-stage near-duplicate detector.

    Stage 1: 256-bit dHash, exact all-pairs Hamming comparison (no bucketing,
             no misses). Hash matches are annotations - every image is still
             embedded and indexed, so hash-matched files remain searchable.
    Stage 2: DINOv2 CLS-token embeddings, L2-normalized, FAISS range search
             (returns ALL pairs above the floor threshold - no top-k cap).
    """

    def __init__(self, model_id, backbone=None):
        self.model_id = model_id
        self.processor, self.model, self.device = backbone or load_backbone(model_id)
        self.dimension = self.model.config.hidden_size

        self.embeddings = np.zeros((0, self.dimension), dtype="float32")
        self.stored_files = []
        self.hash_bits = np.zeros((0, (config.HASH_SIZE ** 2) // 8), dtype="uint8")
        self.index = faiss.IndexFlatIP(self.dimension)

        self.fast_duplicates = []      # hash-confirmed pairs (threshold-independent)
        self.semantic_pairs = []       # all embedding pairs >= SCAN_THRESHOLD_FLOOR
        self.failed_files = []
        self.optimal_threshold = config.DEFAULT_THRESHOLD

    # ------------------------------------------------------------------ embed

    @torch.inference_mode()
    def _embed_images(self, images):
        inputs = self.processor(images=images, return_tensors="pt").to(self.device)
        hidden = self.model(**inputs).last_hidden_state
        vectors = F.normalize(hidden[:, 0], dim=-1)  # CLS token
        return vectors.cpu().numpy().astype("float32")

    def _embed_path(self, image_path):
        try:
            with Image.open(image_path) as im:
                img = im.convert("RGB")
            return self._embed_images([img])
        except Exception:
            return None

    # ------------------------------------------------------------------ index

    def bulk_index(self, folder, progress_cb=None):
        """Hash + embed every readable image under `folder` in true batches."""
        files = sorted(walk_image_files(folder))
        total = len(files)
        if total == 0:
            return

        all_vecs, all_files, all_hashes = [], [], []
        batch_imgs, batch_paths, batch_hashes = [], [], []

        def flush():
            if not batch_imgs:
                return
            try:
                vecs = self._embed_images(batch_imgs)
                all_vecs.append(vecs)
                all_files.extend(batch_paths)
                all_hashes.extend(batch_hashes)
            except Exception:
                # One bad batch should not kill the scan: retry image by image.
                for img, path, hbits in zip(batch_imgs, batch_paths, batch_hashes):
                    try:
                        all_vecs.append(self._embed_images([img]))
                        all_files.append(path)
                        all_hashes.append(hbits)
                    except Exception:
                        self.failed_files.append(path)
            batch_imgs.clear()
            batch_paths.clear()
            batch_hashes.clear()

        for n, path in enumerate(files, 1):
            try:
                with Image.open(path) as im:
                    img = im.convert("RGB")
                hbits = np.packbits(imagehash.dhash(img, hash_size=config.HASH_SIZE).hash)
            except Exception:
                self.failed_files.append(path)
                continue

            batch_imgs.append(img)
            batch_paths.append(path)
            batch_hashes.append(hbits)
            if len(batch_imgs) >= config.BATCH_SIZE:
                flush()
            if progress_cb:
                progress_cb("Indexing images", n, total)
        flush()

        if not all_files:
            return

        self.embeddings = np.vstack(all_vecs)
        self.stored_files = all_files
        self.hash_bits = np.stack(all_hashes)
        self.index = faiss.IndexFlatIP(self.dimension)
        self.index.add(self.embeddings)

        if progress_cb:
            progress_cb("Comparing images", 0, 1)
        self._find_hash_duplicates()
        self.semantic_pairs = self._find_semantic_pairs(config.SCAN_THRESHOLD_FLOOR)
        if progress_cb:
            progress_cb("Comparing images", 1, 1)

    # ------------------------------------------------------- stage 1: hashing

    def _find_hash_duplicates(self):
        """Exact all-pairs Hamming comparison on packed dHash bits."""
        self.fast_duplicates = []
        n = self.hash_bits.shape[0]
        if n < 2:
            return
        bits_total = config.HASH_SIZE ** 2
        chunk = 512
        for start in range(0, n, chunk):
            block = self.hash_bits[start:start + chunk]
            # (chunk, n) Hamming distances via XOR + popcount lookup
            dists = _POPCOUNT[block[:, None, :] ^ self.hash_bits[None, :, :]].sum(axis=2)
            rows, cols = np.nonzero(dists <= config.HASH_THRESHOLD)
            for r, c in zip(rows, cols):
                i, j = start + int(r), int(c)
                if j <= i:
                    continue
                dist = int(dists[r, c])
                self.fast_duplicates.append({
                    "file1": self.stored_files[i],
                    "file2": self.stored_files[j],
                    "score": 1.0 - dist / bits_total,
                    "hash_distance": dist,
                    "method": "dHash",
                })

    # ----------------------------------------------------- stage 2: semantic

    def _find_semantic_pairs(self, threshold):
        """All embedding pairs with cosine >= threshold, via FAISS range search."""
        pairs = []
        n = self.index.ntotal
        if n < 2:
            return pairs
        chunk = 512
        for start in range(0, n, chunk):
            block = self.embeddings[start:start + chunk]
            lims, D, I = self.index.range_search(block, float(threshold))
            for bi in range(block.shape[0]):
                i = start + bi
                for pos in range(lims[bi], lims[bi + 1]):
                    j = int(I[pos])
                    if j <= i:  # dedupe (i, j)/(j, i) and skip self-match
                        continue
                    pairs.append({
                        "file1": self.stored_files[i],
                        "file2": self.stored_files[j],
                        "score": float(D[pos]),
                        "method": "DINOv2",
                    })
        return pairs

    # ------------------------------------------------------------ public API

    def find_duplicates(self, threshold=None):
        """Semantic pairs above threshold, merged with hash pairs.

        Hash pairs are found by Hamming distance, so the cosine threshold
        never filters them out.
        """
        t = self.optimal_threshold if threshold is None else threshold
        results = [p for p in self.semantic_pairs if p["score"] >= t]
        seen = {pair_key(p["file1"], p["file2"]) for p in results}
        for p in self.fast_duplicates:
            if pair_key(p["file1"], p["file2"]) not in seen:
                results.append(p)
        return results

    def find_matches_for_file(self, file_path, threshold=None, top_k=50):
        threshold = self.optimal_threshold if threshold is None else threshold
        if self.index.ntotal == 0:
            return []
        vec = self._embed_path(file_path)
        if vec is None:
            return []
        D, I = self.index.search(vec, min(top_k, self.index.ntotal))
        results = []
        for score, idx in zip(D[0], I[0]):
            if idx != -1 and score >= threshold:
                results.append({
                    "path": self.stored_files[int(idx)],
                    "score": float(score),
                    "method": "DINOv2",
                })
        return results

    def compare_two_images(self, img1_path, img2_path):
        vec1 = self._embed_path(img1_path)
        vec2 = self._embed_path(img2_path)
        if vec1 is None or vec2 is None:
            return None

        similarity = float(np.dot(vec1[0], vec2[0]))

        hash_dist = None
        try:
            with Image.open(img1_path) as im1, Image.open(img2_path) as im2:
                h1 = imagehash.dhash(im1.convert("RGB"), hash_size=config.HASH_SIZE)
                h2 = imagehash.dhash(im2.convert("RGB"), hash_size=config.HASH_SIZE)
            hash_dist = h1 - h2
        except Exception:
            pass

        return {
            "similarity": similarity,
            "hash_distance": hash_dist,
            "match": similarity >= self.optimal_threshold,
        }

    # ------------------------------------------------------------ calibration

    def calibrate_threshold(self, gt_groups, gt_pairs):
        """Pick the F1-optimal threshold on half the ground-truth groups,
        report honest metrics on the held-out half.

        Groups (not pairs) are split so pairs of the same source image never
        leak across the calibration/holdout boundary. Within each split, only
        pairs whose BOTH endpoints belong to that split's files are scored.
        """
        if not gt_pairs:
            return None

        group_ids = sorted(gt_groups)
        rng = random.Random(config.CALIBRATION_SEED)
        rng.shuffle(group_ids)
        half = max(1, len(group_ids) // 2)
        calib_files = {f for g in group_ids[:half] for f in gt_groups[g]}
        holdout_files = {f for g in group_ids[half:] for f in gt_groups[g]}

        thresholds = np.round(np.arange(
            config.CALIBRATION_SWEEP_START,
            config.CALIBRATION_SWEEP_STOP + config.CALIBRATION_SWEEP_STEP / 2,
            config.CALIBRATION_SWEEP_STEP,
        ), 2)

        hash_keys = {pair_key(p["file1"], p["file2"]) for p in self.fast_duplicates}
        sem_sorted = sorted(self.semantic_pairs, key=lambda p: p["score"])
        sem_keys = [pair_key(p["file1"], p["file2"]) for p in sem_sorted]
        sem_scores = np.array([p["score"] for p in sem_sorted])

        history = []
        calib_rows = []
        for t in thresholds:
            start = int(np.searchsorted(sem_scores, t))
            det = set(sem_keys[start:]) | hash_keys
            full = pair_metrics(det, gt_pairs)
            calib = pair_metrics(det, gt_pairs, restrict=calib_files)
            history.append({
                "threshold": float(t),
                "f1": full["f1"], "precision": full["precision"], "recall": full["recall"],
                "count": len(det), "tp": full["tp"], "fp": full["fp"], "fn": full["fn"],
            })
            calib_rows.append((float(t), calib["f1"]))

        best_f1 = max(f1 for _, f1 in calib_rows)
        tied = [t for t, f1 in calib_rows if f1 == best_f1]
        best_thresh = float(tied[len(tied) // 2])  # median of the tied plateau
        self.optimal_threshold = best_thresh

        start = int(np.searchsorted(sem_scores, best_thresh))
        det_best = set(sem_keys[start:]) | hash_keys
        holdout = pair_metrics(det_best, gt_pairs, restrict=holdout_files)

        return {
            "threshold": best_thresh,
            "calibration_f1": best_f1,
            "holdout": holdout,
            "history": history,
            "n_groups": len(group_ids),
            "n_gt_pairs": len(gt_pairs),
        }

    # -------------------------------------------------------- bundle loading

    def load_precomputed(self, embeddings, stored_files, hash_bits):
        """Adopt embeddings computed offline (demo bundle) instead of scanning."""
        self.embeddings = np.asarray(embeddings, dtype="float32")
        self.stored_files = list(stored_files)
        self.hash_bits = np.asarray(hash_bits, dtype="uint8")
        self.failed_files = []
        self._rebuild()

    # ------------------------------------------------------ delete / restore

    def remove_files(self, paths):
        """Drop files from the index and pair lists. Returns a payload that
        restore_files() can use to undo the removal without re-embedding."""
        targets = {norm_path(p) for p in paths}
        keep, removed_idx = [], []
        for i, f in enumerate(self.stored_files):
            (removed_idx if norm_path(f) in targets else keep).append(i)
        if not removed_idx:
            return None

        payload = {
            "files": [self.stored_files[i] for i in removed_idx],
            "vecs": self.embeddings[removed_idx].copy(),
            "hashes": self.hash_bits[removed_idx].copy(),
        }
        self.embeddings = self.embeddings[keep]
        self.stored_files = [self.stored_files[i] for i in keep]
        self.hash_bits = self.hash_bits[keep]
        self._rebuild()
        return payload

    def restore_files(self, payload):
        if not payload:
            return
        self.embeddings = np.vstack([self.embeddings, payload["vecs"]])
        self.stored_files = self.stored_files + list(payload["files"])
        self.hash_bits = np.vstack([self.hash_bits, payload["hashes"]])
        self._rebuild()

    def _rebuild(self):
        self.index = faiss.IndexFlatIP(self.dimension)
        if len(self.stored_files):
            self.index.add(self.embeddings)
        self._find_hash_duplicates()
        self.semantic_pairs = (
            self._find_semantic_pairs(config.SCAN_THRESHOLD_FLOOR)
            if len(self.stored_files) >= 2 else []
        )
