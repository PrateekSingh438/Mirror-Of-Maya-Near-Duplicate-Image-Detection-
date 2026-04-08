import os
import networkx as nx
from collections import defaultdict
import config

def walk_image_files(folder):
    for root, _, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(config.SUPPORTED_EXTENSIONS):
                yield os.path.join(root, f)

def normalize_pair_fullpath(pair):
    b1 = os.path.splitext(os.path.basename(pair[0]))[0]
    b2 = os.path.splitext(os.path.basename(pair[1]))[0]
    return tuple(sorted((b1, b2)))

def is_original_file(filepath):
    normalized = filepath.replace('\\', '/')
    return 'original' in normalized.lower().split('/')

def get_basename_without_ext(filepath):
    return os.path.splitext(os.path.basename(filepath))[0]

def generate_ground_truth(dataset_path):
    files = list(walk_image_files(dataset_path))
    
    originals = {}
    attacks = defaultdict(list)
    
    print(f"\nAnalyzing {len(files)} files...")
    
    for f in files:
        basename = get_basename_without_ext(f)
        
        if is_original_file(f):
            originals[basename] = f
        else:
            attacks[basename].append(f)
    
    # Generate pairs
    pairs = []
    for basename, original_path in originals.items():
        if basename in attacks:
            for attack_path in attacks[basename]:
                pairs.append((original_path, attack_path))
    
    print(f"Ground Truth: {len(originals)} originals, {len(pairs)} pairs")
    
    return pairs

def organize_clusters(duplicates, mode="basename"):
    if not duplicates:
        return []
    
    if mode == "basename":
        return _cluster_by_basename(duplicates)
    else:
        return _cluster_by_graph(duplicates)

def _cluster_by_basename(duplicates):
    basename_groups = defaultdict(lambda: {'files': set(), 'pairs': []})
    
    for dup in duplicates:
        f1, f2 = dup['file1'], dup['file2']
        b1 = get_basename_without_ext(f1)
        b2 = get_basename_without_ext(f2)
        
        #matching basenames
        if b1 == b2:
            basename_groups[b1]['files'].add(f1)
            basename_groups[b1]['files'].add(f2)
            basename_groups[b1]['pairs'].append(dup)
    
    clusters = []
    
    for basename, data in basename_groups.items():
        files = list(data['files'])
        if len(files) < 2:
            continue
        
        # Build graph
        G = nx.Graph()
        for dup in data['pairs']:
            G.add_edge(dup['file1'], dup['file2'], weight=dup['score'])
        
        original = _select_original(files, G)
        dups_list = _get_duplicates_from_graph(files, original, G)
        
        if dups_list:
            clusters.append({'original': original, 'duplicates': dups_list})
    
    return sorted(clusters, key=lambda x: len(x['duplicates']), reverse=True)

def _cluster_by_graph(duplicates):
    G = nx.Graph()
    
    for d in duplicates:
        G.add_edge(d['file1'], d['file2'], weight=d['score'])
    
    clusters = []
    
    for component in nx.connected_components(G):
        if len(component) < 2:
            continue
        
        component_list = list(component)
        subgraph = G.subgraph(component)
        
        original = _select_original(component_list, subgraph)
        dups_list = _get_duplicates_from_graph(component_list, original, subgraph)
        
        if dups_list:
            clusters.append({'original': original, 'duplicates': dups_list})
    
    return sorted(clusters, key=lambda x: len(x['duplicates']), reverse=True)

def _select_original(candidates, graph):
    for c in candidates:
        if is_original_file(c):
            return c
    
    # Highest average similarity to neighbors
    scores = {}
    for c in candidates:
        neighbors = list(graph.neighbors(c))
        if neighbors:
            avg_weight = sum(graph[c][n]['weight'] for n in neighbors) / len(neighbors)
            scores[c] = avg_weight
    
    if scores:
        return max(scores.items(), key=lambda x: x[1])[0]
    return min(candidates, key=lambda x: len(os.path.basename(x)))

def _get_duplicates_from_graph(files, original, graph):
    dups_list = []
    
    for node in files:
        if node == original:
            continue
        

        if graph.has_edge(original, node):
            score = graph[original][node]['weight']
        else:
            try:
                path = nx.shortest_path(graph, original, node)
                scores = []
                for i in range(len(path)-1):
                    scores.append(graph[path[i]][path[i+1]]['weight'])
                score = sum(scores) / len(scores)
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue
        
        dups_list.append({'path': node, 'score': float(score)})
    
    return sorted(dups_list, key=lambda x: x['score'], reverse=True)

def get_dir_size(path):
    total = 0
    try:
        for f in walk_image_files(path):
            total += os.path.getsize(f)
    except OSError:
        pass
    return total / (1024 * 1024)

def calculate_wasted_space(duplicates):
    seen = set()
    total = 0

    for d in duplicates:
        if d['file2'] not in seen:
            try:
                total += os.path.getsize(d['file2'])
                seen.add(d['file2'])
            except OSError:
                pass
    
    return total / (1024 * 1024)

def format_file_size(bytes_size):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"

def get_image_files(folder):
    return list(walk_image_files(folder))