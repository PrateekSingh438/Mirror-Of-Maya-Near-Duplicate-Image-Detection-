import os
import networkx as nx
from collections import defaultdict
import config

def walk_image_files(folder):
    """Generator that yields all image file paths in folder recursively"""
    for root, _, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(config.SUPPORTED_EXTENSIONS):
                yield os.path.join(root, f)

def normalize_pair(pair):
    """Normalize file pair to ID tuple for comparison"""
    n1 = os.path.splitext(os.path.basename(pair[0]))[0]
    n2 = os.path.splitext(os.path.basename(pair[1]))[0]
    return tuple(sorted((n1, n2)))

def is_original_file(filepath):
    """Check if file is in the original folder"""
    return config.ORIGINAL_DIR_NAME.lower() in filepath.lower()

def auto_generate_ground_truth(folder):
    """
    Generate ground truth pairs by grouping files with same basename.
    Works for datasets where originals and duplicates share filenames.
    """
    files = list(walk_image_files(folder))
    base_map = defaultdict(list)
    
    for f in files:
        name = os.path.splitext(os.path.basename(f))[0]
        base_map[name].append(f)
    
    pairs = []
    for base, group in base_map.items():
        if len(group) > 1:
            # Create all pairwise combinations
            for i in range(len(group)):
                for j in range(i+1, len(group)):
                    pairs.append((group[i], group[j]))
    
    return pairs

def organize_clusters(duplicates):
    """
    Organize duplicates into clusters using graph-based approach.
    Each cluster has one original and multiple duplicates.
    FIXED: Now properly ensures originals are not compared to other duplicates.
    """
    if not duplicates:
        return []
    
    # Build graph
    G = nx.Graph()
    for d in duplicates:
        G.add_edge(d['file1'], d['file2'], weight=d['score'])
    
    clusters = []
    
    for component in nx.connected_components(G):
        if len(component) < 2:
            continue
        
        subgraph = G.subgraph(component)
        candidates = list(component)
        
        # Identify original using multiple heuristics
        original = select_original(candidates, subgraph)
        
        # Build duplicate list with scores - ONLY include files that are NOT the original
        dups_list = []
        for node in component:
            if node == original:
                continue
            
            # Get score relative to original
            if subgraph.has_edge(original, node):
                score = subgraph[original][node]['weight']
            else:
                # Calculate average score along shortest path
                try:
                    path = nx.shortest_path(subgraph, original, node)
                    scores = []
                    for i in range(len(path)-1):
                        u, v = path[i], path[i+1]
                        scores.append(subgraph[u][v]['weight'])
                    score = sum(scores) / len(scores)
                except:
                    score = 0.01
            
            dups_list.append({
                'path': node,
                'score': float(score)
            })
        
        # Sort by score descending
        dups_list.sort(key=lambda x: x['score'], reverse=True)
        
        clusters.append({
            'original': original,
            'duplicates': dups_list
        })
    
    # Sort clusters by number of duplicates
    clusters.sort(key=lambda x: len(x['duplicates']), reverse=True)
    return clusters

def select_original(candidates, subgraph):
    """
    Select the most likely original file using heuristics:
    1. Prefers files in 'original' folder
    2. Prefers files with higher average connectivity
    3. Prefers shorter filenames (less likely to have suffixes)
    """
    # Check for files in original folder
    for candidate in candidates:
        if is_original_file(candidate):
            return candidate
    
    # Calculate average edge weight for each candidate
    scores = {}
    for candidate in candidates:
        neighbors = list(subgraph.neighbors(candidate))
        if neighbors:
            avg_weight = sum(subgraph[candidate][n]['weight'] for n in neighbors) / len(neighbors)
            scores[candidate] = avg_weight
    
    if scores:
        # Return candidate with highest average similarity
        return max(scores.items(), key=lambda x: x[1])[0]
    
    # Fallback: shortest filename
    return min(candidates, key=lambda x: len(os.path.basename(x)))

def count_total_duplicates(clusters):
    """
    Count total number of duplicate files (not pairs).
    This gives the actual count of files that are duplicates.
    """
    total = 0
    for cluster in clusters:
        total += len(cluster['duplicates'])
    return total

def get_dir_size(path):
    """Calculate total size of all images in directory (in MB)"""
    total = 0
    try:
        for f in walk_image_files(path):
            total += os.path.getsize(f)
    except:
        pass
    return total / (1024 * 1024)

def calculate_wasted_space(duplicates):
    """
    Calculate total wasted space from duplicates (in MB).
    Only counts each duplicate file once.
    """
    seen = set()
    total = 0
    
    for d in duplicates:
        # Count file2 as the duplicate
        if d['file2'] not in seen:
            try:
                total += os.path.getsize(d['file2'])
                seen.add(d['file2'])
            except:
                pass
    
    return total / (1024 * 1024)

def format_file_size(bytes_size):
    """Format bytes into human-readable size"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"

def get_image_files(folder):
    """Get list of all image files in folder"""
    return list(walk_image_files(folder))

def calculate_image_quality(image_path):
    """
    Calculate quality score for an image based on multiple metrics.
    Returns score from 0-100.
    """
    try:
        from PIL import Image
        import numpy as np
        from scipy import ndimage
        
        img = Image.open(image_path)
        img_array = np.array(img.convert('L'))  # Convert to grayscale
        
        # 1. Sharpness (Laplacian variance)
        laplacian = ndimage.laplace(img_array)
        sharpness = laplacian.var()
        
        # 2. Entropy (information content)
        histogram, _ = np.histogram(img_array, bins=256, range=(0, 256))
        histogram = histogram / histogram.sum()
        entropy = -np.sum(histogram * np.log2(histogram + 1e-10))
        
        # 3. Resolution score
        width, height = img.size
        megapixels = (width * height) / 1_000_000
        resolution_score = min(megapixels / 10, 1.0)  # Normalize to 0-1
        
        # 4. JPEG blockiness detection (simple version)
        blockiness = detect_blockiness(img_array)
        
        # Combine scores
        quality = (
            (min(sharpness / 100, 1.0) * config.SHARPNESS_WEIGHT) +
            (entropy / 8.0 * config.ENTROPY_WEIGHT) +
            (resolution_score * config.RESOLUTION_WEIGHT) -
            (blockiness * config.BLOCKINESS_PENALTY)
        ) * 100
        
        return max(0, min(100, quality))
    except:
        return 50  # Default score if calculation fails

def detect_blockiness(img_array):
    """Detect JPEG compression artifacts (8x8 blocking)"""
    try:
        # Calculate differences at 8-pixel intervals
        diff_h = np.abs(np.diff(img_array[:, ::8], axis=1))
        diff_v = np.abs(np.diff(img_array[::8, :], axis=0))
        
        blockiness = (diff_h.mean() + diff_v.mean()) / 2
        return min(blockiness / 50, 1.0)  # Normalize
    except:
        return 0

def create_original_duplicate_pairs(clusters):
    """
    Create a list of (original, duplicate) pairs from clusters.
    This ensures File 1 is always an original, File 2 is always a duplicate.
    """
    pairs = []
    for cluster in clusters:
        original = cluster['original']
        for dup in cluster['duplicates']:
            pairs.append({
                'file1': original,
                'file2': dup['path'],
                'score': dup['score'],
                'method': 'Clustered'
            })
    return pairs