import os
import re
import itertools
from collections import defaultdict

import networkx as nx
from PIL import Image

import config


# ----------------------------------------------------------------- paths

def norm_path(p):
    """Canonical form used everywhere paths are compared."""
    return os.path.normcase(os.path.normpath(os.path.abspath(p)))


def pair_key(f1, f2):
    return tuple(sorted((norm_path(f1), norm_path(f2))))


def walk_image_files(folder):
    for root, dirs, files in os.walk(folder):
        # never index soft-deleted files
        dirs[:] = [d for d in dirs if d != config.TRASH_DIR_NAME]
        for f in files:
            if f.lower().endswith(config.SUPPORTED_EXTENSIONS):
                yield os.path.join(root, f)


def get_basename_without_ext(filepath):
    return os.path.splitext(os.path.basename(filepath))[0]


def is_original_file(filepath):
    return 'original' in norm_path(filepath).replace('\\', '/').lower().split('/')


# ----------------------------------------------------------- ground truth

# Filenames are used ONLY here, to build the evaluation ground truth.
# Detection itself never looks at filenames.

_AUG_SUFFIX = re.compile(r'_aug_[a-z0-9]+$', re.IGNORECASE)


def source_id(filepath):
    """Which source image does this file derive from?

    Convention 1 (copydays): copies keep the same basename in different
    folders, e.g. original/200000.jpg and jpeg/10/200000.jpg.
    Convention 2 (generated sets): copies append an _aug_* suffix,
    e.g. berlin_1_aug_crop.jpg derives from berlin_1.jpg.
    """
    return _AUG_SUFFIX.sub('', get_basename_without_ext(filepath))


def generate_ground_truth(dataset_path):
    """Return (groups, gt_pairs).

    groups: source-id -> set of normalized full paths (only groups with 2+
    files). gt_pairs: every within-group pair (the full closure - an attack
    matching another attack of the same source is a correct detection).
    Returns (None, None) when the dataset has no recognizable structure,
    in which case the UI hides evaluation instead of showing a fake score.
    """
    groups = defaultdict(set)
    for f in walk_image_files(dataset_path):
        groups[source_id(f)].add(norm_path(f))

    groups = {k: v for k, v in groups.items() if len(v) > 1}
    if not groups:
        return None, None

    gt_pairs = set()
    for files in groups.values():
        for a, b in itertools.combinations(sorted(files), 2):
            gt_pairs.add(tuple(sorted((a, b))))
    return groups, gt_pairs


# ----------------------------------------------------------------- metrics

def pair_metrics(det_pairs, gt_pairs, restrict=None):
    """Pairwise precision / recall / F1 over full-path pairs.

    `restrict` limits both sets to pairs whose BOTH endpoints are in the
    given file set (used for the calibration/holdout split).
    """
    det, gt = set(det_pairs), set(gt_pairs)
    if restrict is not None:
        det = {p for p in det if p[0] in restrict and p[1] in restrict}
        gt = {p for p in gt if p[0] in restrict and p[1] in restrict}

    tp = len(det & gt)
    fp = len(det - gt)
    fn = len(gt - det)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"tp": tp, "fp": fp, "fn": fn,
            "precision": precision, "recall": recall, "f1": f1}


def duplicates_to_pairset(duplicates):
    return {pair_key(d["file1"], d["file2"]) for d in duplicates}


def per_attack_recall(clusters, gt_groups, dataset_path):
    """For each attack folder (e.g. jpeg/10, crops/crop_50_percent): what
    fraction of its files ended up in the same predicted cluster as their
    source image? Returns a list of {attack, found, total, recall} rows."""
    if not gt_groups:
        return []

    file_to_cluster = {}
    for ci, c in enumerate(clusters):
        for m in [c["original"]] + [d["path"] for d in c["duplicates"]]:
            file_to_cluster[norm_path(m)] = ci

    dataset_path = norm_path(dataset_path)
    counts = defaultdict(lambda: [0, 0])  # attack label -> [found, total]

    for gid, files in gt_groups.items():
        originals = [f for f in files if is_original_file(f)]
        if not originals:
            # generated sets: the file named exactly like the source id
            originals = [f for f in files if get_basename_without_ext(f) == gid]
        if not originals:
            originals = [sorted(files)[0]]
        origin = originals[0]
        origin_cluster = file_to_cluster.get(origin)

        for f in files:
            if f == origin:
                continue
            try:
                label = os.path.dirname(os.path.relpath(f, dataset_path)).replace('\\', '/')
            except ValueError:
                label = os.path.basename(os.path.dirname(f))
            label = label or "(top level)"
            counts[label][1] += 1
            if origin_cluster is not None and file_to_cluster.get(f) == origin_cluster:
                counts[label][0] += 1

    rows = [{"attack": k, "found": v[0], "total": v[1],
             "recall": v[0] / v[1] if v[1] else 0.0}
            for k, v in sorted(counts.items())]
    return rows


# -------------------------------------------------------------- clustering

def organize_clusters(duplicates):
    """Group duplicate pairs into clusters via graph connected components.
    Filenames play no role here."""
    if not duplicates:
        return []

    G = nx.Graph()
    for d in duplicates:
        G.add_edge(d['file1'], d['file2'], weight=d['score'])

    clusters = []
    for component in nx.connected_components(G):
        if len(component) < 2:
            continue
        members = list(component)
        subgraph = G.subgraph(component)
        original = _select_original(members, subgraph)
        dups_list = _duplicates_from_graph(members, original, subgraph)
        if dups_list:
            clusters.append({'original': original, 'duplicates': dups_list})

    return sorted(clusters, key=lambda x: len(x['duplicates']), reverse=True)


def _image_pixels(path):
    try:
        with Image.open(path) as img:
            w, h = img.size
        return w * h
    except Exception:
        return 0


def _select_original(candidates, graph):
    """Pick the best file to keep: an 'original' folder hint wins, otherwise
    the highest-resolution file (ties broken by file size)."""
    hinted = [c for c in candidates if is_original_file(c)]
    if hinted:
        return hinted[0]

    def quality(path):
        try:
            size = os.path.getsize(path)
        except OSError:
            size = 0
        return (_image_pixels(path), size)

    return max(candidates, key=quality)


def _duplicates_from_graph(files, original, graph):
    dups_list = []
    for node in files:
        if node == original:
            continue
        if graph.has_edge(original, node):
            score = graph[original][node]['weight']
        else:
            try:
                path = nx.shortest_path(graph, original, node)
                hops = [graph[path[i]][path[i + 1]]['weight'] for i in range(len(path) - 1)]
                score = sum(hops) / len(hops)
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue
        dups_list.append({'path': node, 'score': float(score)})
    return sorted(dups_list, key=lambda x: x['score'], reverse=True)


# ------------------------------------------------------------------- misc

def get_dir_size(path):
    total = 0
    try:
        for f in walk_image_files(path):
            total += os.path.getsize(f)
    except OSError:
        pass
    return total / (1024 * 1024)


def calculate_wasted_space(clusters):
    """MB used by deletable copies: every cluster member except the kept
    original. Pair lists can't be used here - a pair's file1/file2 order is
    arbitrary, so summing one side may count the original as waste."""
    seen = set()
    total = 0
    for c in clusters:
        for d in c['duplicates']:
            key = norm_path(d['path'])
            if key not in seen:
                seen.add(key)
                try:
                    total += os.path.getsize(d['path'])
                except OSError:
                    pass
    return total / (1024 * 1024)


def filter_at_threshold(all_duplicates, threshold):
    """Hash-confirmed pairs are exact copies; the cosine slider never hides them."""
    return [d for d in all_duplicates
            if d.get('method') == 'dHash' or d['score'] >= threshold]


def format_file_size(bytes_size):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"
