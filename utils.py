import os
import networkx as nx
from collections import defaultdict
import config

def walk_image_files(folder):
    for root, _, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(config.SUPPORTED_EXTENSIONS):
                yield os.path.join(root, f)

def normalize_pair(pair):
    """
    For datasets where same basename = same image (like COPYDAYS).
    This is your current approach - keeps it for reference.
    """
    n1 = os.path.splitext(os.path.basename(pair[0]))[0]
    n2 = os.path.splitext(os.path.basename(pair[1]))[0]
    return tuple(sorted((n1, n2)))
def is_original_file(filepath):
    normalized_path = filepath.replace('\\', '/')
    path_parts = normalized_path.lower().split('/')
    return 'original' in path_parts

def get_basename_without_ext(filepath):
    """Extract basename without extension"""
    return os.path.splitext(os.path.basename(filepath))[0]

def generate_proper_ground_truth(dataset_path):
    """Generate ground truth pairs: original → attack only"""
    files = list(walk_image_files(dataset_path))
    
    originals = {}
    attacks = defaultdict(list)
    
    print(f"\n🔍 Analyzing {len(files)} files...")
    
    original_count = 0
    attack_count = 0
    
    for f in files:
        basename = get_basename_without_ext(f)
        
        if is_original_file(f):
            originals[basename] = f
            original_count += 1
            if original_count <= 3:
                print(f"   ✓ Original: {f}")
        else:
            attacks[basename].append(f)
            attack_count += 1
    
    print(f"\n   Total originals: {original_count}")
    print(f"   Total attacks: {attack_count}")
    
    pairs = []
    for basename, original_path in originals.items():
        if basename in attacks:
            for attack_path in attacks[basename]:
                pairs.append((original_path, attack_path))
    
    print(f"\n📊 Ground Truth Stats:")
    print(f"   Originals: {len(originals)}")
    print(f"   Unique basenames with attacks: {len([b for b in originals if b in attacks])}")
    print(f"   Total attacks: {sum(len(v) for v in attacks.values())}")
    print(f"   Valid pairs (original→attack): {len(pairs)}")
    
    if len(pairs) > 0:
        print(f"\n✓ Sample pairs:")
        for i, (orig, attack) in enumerate(pairs[:5]):
            print(f"   {i+1}. {os.path.basename(orig)} → {attack.replace(dataset_path, '...').replace(os.sep, '/')}")
    
    return pairs

def organize_clusters(duplicates, mode="basename"):
    """
    Organize duplicates into clusters with two modes:
    
    mode="basename": Only cluster images with same basename (conservative, like query tab)
    mode="semantic": Cluster all semantically similar images (may include unrelated)
    """
    if not duplicates:
        return []
    
    print(f"\n🔧 Organizing {len(duplicates)} duplicate pairs (mode: {mode})...")
    
    if mode == "basename":
        return _organize_clusters_basename_filtered(duplicates)
    else:
        return _organize_clusters_semantic(duplicates)

def _organize_clusters_basename_filtered(duplicates):
    """
    CONSERVATIVE MODE: Only cluster images that share the same basename
    
    This mimics the query tab behavior - only shows duplicates that are
    actually variations of the same original image.
    
    Example:
    - 200000.jpg (original)
    - 200000.jpg (jpeg/75/200000.jpg) ✓ Same basename - included
    - 200100.jpg (jpeg/75/200100.jpg) ✗ Different basename - separate cluster
    """
    
    # Group duplicates by basename
    basename_groups = defaultdict(lambda: {'files': set(), 'pairs': []})
    
    for dup in duplicates:
        file1 = dup['file1']
        file2 = dup['file2']
        
        basename1 = get_basename_without_ext(file1)
        basename2 = get_basename_without_ext(file2)
        
        # CRITICAL: Only process pairs with SAME basename
        if basename1 == basename2:
            basename_groups[basename1]['files'].add(file1)
            basename_groups[basename1]['files'].add(file2)
            basename_groups[basename1]['pairs'].append(dup)
    
    print(f"   Found {len(basename_groups)} unique basenames")
    
    clusters = []
    
    for basename, data in basename_groups.items():
        files = list(data['files'])
        
        if len(files) < 2:
            continue
        
        # Build subgraph for this basename only
        G = nx.Graph()
        for dup in data['pairs']:
            G.add_edge(dup['file1'], dup['file2'], weight=dup['score'])
        
        # Select original
        original = select_original(files, G)
        
        # Get duplicates
        dups_list = []
        for node in files:
            if node == original:
                continue
            
            if G.has_edge(original, node):
                score = G[original][node]['weight']
            else:
                try:
                    path = nx.shortest_path(G, original, node)
                    scores = []
                    for i in range(len(path)-1):
                        u, v = path[i], path[i+1]
                        scores.append(G[u][v]['weight'])
                    score = sum(scores) / len(scores)
                except:
                    continue
            
            dups_list.append({
                'path': node,
                'score': float(score)
            })
        
        if dups_list:
            dups_list.sort(key=lambda x: x['score'], reverse=True)
            clusters.append({
                'original': original,
                'duplicates': dups_list
            })
    
    clusters.sort(key=lambda x: len(x['duplicates']), reverse=True)
    
    print(f"✅ Created {len(clusters)} clusters (basename-filtered)")
    
    return clusters

def _organize_clusters_semantic(duplicates):
    """
    SEMANTIC MODE: Cluster all similar images regardless of basename
    
    This can group unrelated images if they happen to be similar.
    Use with caution at low thresholds.
    """
    
    G = nx.Graph()
    
    for d in duplicates:
        G.add_edge(d['file1'], d['file2'], weight=d['score'])
    
    print(f"   Graph has {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
    
    clusters = []
    
    components = list(nx.connected_components(G))
    print(f"   Found {len(components)} connected components")
    
    for component in components:
        if len(component) < 2:
            continue
        
        component_list = list(component)
        subgraph = G.subgraph(component)
        
        original = select_original(component_list, subgraph)
        
        dups_list = []
        
        for node in component_list:
            if node == original:
                continue
            
            if subgraph.has_edge(original, node):
                score = subgraph[original][node]['weight']
            else:
                try:
                    path = nx.shortest_path(subgraph, original, node)
                    scores = []
                    for i in range(len(path)-1):
                        u, v = path[i], path[i+1]
                        scores.append(subgraph[u][v]['weight'])
                    score = sum(scores) / len(scores)
                except:
                    continue
            
            dups_list.append({
                'path': node,
                'score': float(score)
            })
        
        if dups_list:
            dups_list.sort(key=lambda x: x['score'], reverse=True)
            clusters.append({
                'original': original,
                'duplicates': dups_list
            })
    
    clusters.sort(key=lambda x: len(x['duplicates']), reverse=True)
    
    print(f"✅ Created {len(clusters)} clusters (semantic)")
    
    return clusters

def select_original(candidates, subgraph):
    """Select the best 'original' from a cluster"""
    for candidate in candidates:
        if is_original_file(candidate):
            return candidate
    
    scores = {}
    for candidate in candidates:
        neighbors = list(subgraph.neighbors(candidate))
        if neighbors:
            avg_weight = sum(subgraph[candidate][n]['weight'] for n in neighbors) / len(neighbors)
            scores[candidate] = avg_weight
    
    if scores:
        return max(scores.items(), key=lambda x: x[1])[0]
    
    return min(candidates, key=lambda x: len(os.path.basename(x)))

def get_dir_size(path):
    total = 0
    try:
        for f in walk_image_files(path):
            total += os.path.getsize(f)
    except:
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
            except:
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