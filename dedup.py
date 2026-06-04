"""Clustering, calibration and evaluation metrics.

Pure logic over embeddings / FAISS indices and id lists — no Streamlit, no
filesystem assumptions in the hot path — so it is reused by the offline indexer,
the stateless (Mode B) path, and the serving app.
"""

import os

import networkx as nx
import numpy as np

from config import CFG


# --------------------------------------------------------------------------- #
# Filesystem + ground-truth helpers
# --------------------------------------------------------------------------- #
def walk_image_files(folder):
    for root, _, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(CFG.SUPPORTED_EXTENSIONS):
                yield os.path.join(root, f)


def identity_of(path):
    """Source-image identity used for ground truth.

    COPYDAYS-style datasets encode the source image in the filename
    (original/200000.jpg, jpeg/10/200000.jpg, crops/.../200000.jpg all share
    identity '200000'). This is a label from the dataset's known structure, not
    from the detector — so using it as ground truth is not circular.
    """
    return os.path.splitext(os.path.basename(path))[0]


def is_original(path):
    norm = path.replace("\\", "/").lower()
    return CFG.ORIGINAL_DIR_NAME in norm.split("/")


def pair_key(a, b):
    return tuple(sorted((str(a), str(b))))


def ground_truth_pairs(paths):
    """All unordered pairs of paths that share a source identity."""
    groups = {}
    for p in paths:
        groups.setdefault(identity_of(p), []).append(p)
    gt = set()
    for members in groups.values():
        if len(members) < 2:
            continue
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                gt.add(pair_key(members[i], members[j]))
    return gt


# --------------------------------------------------------------------------- #
# Candidate pair generation from a FAISS index
# --------------------------------------------------------------------------- #
def find_semantic_pairs(index, ids, threshold, top_k=50, hash_pairs=None):
    """Return de-duplicated candidate pairs above `threshold`.

    `index` is a FAISS IndexFlatIP (normalized vectors); `ids[i]` labels row i.
    `hash_pairs` (optional) are exact-match pairs from the dHash stage, injected
    with score 1.0 and method 'dHash'.
    """
    pairs = []
    seen = set()

    if hash_pairs:
        for hp in hash_pairs:
            key = pair_key(hp["a"], hp["b"])
            if key not in seen:
                seen.add(key)
                pairs.append({"a": hp["a"], "b": hp["b"],
                              "score": 1.0, "method": "dHash"})

    n = index.ntotal
    if n < 2:
        return pairs

    k = min(top_k, n)
    chunk = 1000
    for start in range(0, n, chunk):
        end = min(start + chunk, n)
        vecs = index.reconstruct_n(start, end - start)
        D, I = index.search(vecs, k)
        for i in range(len(vecs)):
            abs_i = start + i
            for rank in range(1, k):
                j = int(I[i][rank])
                score = float(D[i][rank])
                if j == -1 or j == abs_i or score < threshold:
                    continue
                key = pair_key(ids[abs_i], ids[j])
                if key in seen:
                    continue
                seen.add(key)
                pairs.append({"a": ids[abs_i], "b": ids[j],
                              "score": score, "method": "DINOv2"})
    return pairs


# --------------------------------------------------------------------------- #
# Metrics + calibration
# --------------------------------------------------------------------------- #
def metrics(detected_set, gt_set):
    tp = len(detected_set & gt_set)
    fp = len(detected_set - gt_set)
    fn = len(gt_set - detected_set)
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return {"precision": prec, "recall": rec, "f1": f1,
            "tp": tp, "fp": fp, "fn": fn}


def calibrate(pairs, gt_set, thresholds=None, objective=None,
              target_precision=None, target_recall=None):
    """Sweep thresholds, return (best_threshold, best_f1, history).

    `pairs` must be generated at or below min(thresholds) so every threshold is a
    pure filter. `history` rows carry the full P/R/F1 (the PR curve).
    """
    thresholds = thresholds or CFG.CALIBRATION_THRESHOLDS
    objective = objective or CFG.CALIBRATION_OBJECTIVE
    target_precision = (CFG.TARGET_PRECISION if target_precision is None
                        else target_precision)
    target_recall = (CFG.TARGET_RECALL if target_recall is None
                     else target_recall)

    history = []
    for t in thresholds:
        det = {pair_key(d["a"], d["b"]) for d in pairs if d["score"] >= t}
        m = metrics(det, gt_set)
        history.append({"threshold": round(float(t), 4), "count": len(det), **m})

    best_t, best_f1, best_key = CFG.DEFAULT_THRESHOLD, 0.0, -1.0
    for row in history:
        if objective == "target_precision":
            key = row["recall"] if row["precision"] >= target_precision else -1.0
        elif objective == "target_recall":
            key = row["precision"] if row["recall"] >= target_recall else -1.0
        else:
            key = row["f1"]
        # ">" (not ">=") keeps the *lowest* threshold among ties -> better recall.
        if key > best_key:
            best_key, best_t, best_f1 = key, row["threshold"], row["f1"]
    return best_t, best_f1, history


# --------------------------------------------------------------------------- #
# Clustering
# --------------------------------------------------------------------------- #
def cluster_pairs(pairs, meta=None, mode="semantic"):
    """Group above-threshold pairs into clusters via connected components.

    `meta` maps id -> dict (may contain 'is_original', 'pixels', 'rel_path').
    Each cluster picks one canonical original and lists the rest as duplicates
    with their similarity to the original.
    """
    meta = meta or {}
    if not pairs:
        return []

    if mode == "basename":
        pairs = [p for p in pairs
                 if identity_of(str(p["a"])) == identity_of(str(p["b"]))]

    G = nx.Graph()
    for p in pairs:
        G.add_edge(p["a"], p["b"], weight=p["score"])

    clusters = []
    for comp in nx.connected_components(G):
        if len(comp) < 2:
            continue
        members = list(comp)
        sub = G.subgraph(comp)
        original = _select_original(members, sub, meta)
        dups = _duplicates_from(members, original, sub)
        if dups:
            clusters.append({"original": original, "duplicates": dups})
    return sorted(clusters, key=lambda c: len(c["duplicates"]), reverse=True)


def _select_original(members, graph, meta):
    # 1) anything explicitly flagged / pathed as an original
    for m in members:
        info = meta.get(m, {})
        if info.get("is_original") or is_original(str(m)):
            return m
    # 2) highest resolution if known
    sized = [(m, meta.get(m, {}).get("pixels", 0)) for m in members]
    if any(px for _, px in sized):
        return max(sized, key=lambda x: x[1])[0]
    # 3) most central node (highest avg similarity)
    scores = {}
    for m in members:
        nbrs = list(graph.neighbors(m))
        if nbrs:
            scores[m] = sum(graph[m][n]["weight"] for n in nbrs) / len(nbrs)
    if scores:
        return max(scores, key=scores.get)
    return members[0]


def _duplicates_from(members, original, graph):
    dups = []
    for node in members:
        if node == original:
            continue
        if graph.has_edge(original, node):
            score = graph[original][node]["weight"]
        else:
            try:
                path = nx.shortest_path(graph, original, node)
                edge_scores = [graph[path[i]][path[i + 1]]["weight"]
                               for i in range(len(path) - 1)]
                score = float(np.mean(edge_scores))
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue
        dups.append({"id": node, "score": float(score)})
    return sorted(dups, key=lambda d: d["score"], reverse=True)
