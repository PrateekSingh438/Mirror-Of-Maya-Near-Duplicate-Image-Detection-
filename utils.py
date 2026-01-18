import os
from collections import defaultdict
from PIL import Image
import config

def get_image_files(directory):
    
    if not os.path.exists(directory):
        return []
    return [
        os.path.join(directory, f) 
        for f in os.listdir(directory) 
        if f.lower().endswith(config.SUPPORTED_IMAGE_EXTENSIONS)
    ]

def get_dir_size(start_path='.'):
    
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            if f.lower().endswith(config.SUPPORTED_IMAGE_EXTENSIONS):
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
    return total_size / config.BYTES_TO_MB

def auto_generate_ground_truth(folder_path):
    """
    Generate ground truth pairs for Copydays dataset.
    Only pairs original images with their attack versions.
    Does NOT pair attack versions with each other.
    """
    original_folder = os.path.join(folder_path, "original")
    
    if not os.path.exists(original_folder):
        print("Warning: No 'original' folder found. Ground truth may be incorrect.")
        return _generate_ground_truth_fallback(folder_path)
    
    # Get all original images
    originals = {}
    for f in os.listdir(original_folder):
        if f.lower().endswith(config.SUPPORTED_IMAGE_EXTENSIONS):
            file_id = os.path.splitext(f)[0]
            originals[file_id] = os.path.join(original_folder, f)
    
    # Find all attack versions and pair with originals only
    gt_pairs = []
    
    for root, dirs, filenames in os.walk(folder_path):
        # Skip the original folder itself
        if "original" in root:
            continue
        
        for f in filenames:
            if f.lower().endswith(config.SUPPORTED_IMAGE_EXTENSIONS):
                file_id = os.path.splitext(f)[0]
                
                # If this attack has a corresponding original
                if file_id in originals:
                    attack_path = os.path.join(root, f)
                    original_path = originals[file_id]
                    
                    # Create pair (always original first for consistency)
                    pair = tuple(sorted((original_path, attack_path)))
                    gt_pairs.append(pair)
    
    print(f"Generated {len(gt_pairs)} ground truth pairs (originals ↔ attacks only)")
    return gt_pairs

def _generate_ground_truth_fallback(folder_path):
    """
    Fallback method for datasets without clear original folder.
    Groups by filename but only pairs each file with others once.
    """
    id_map = defaultdict(list)
    
    for root, _, filenames in os.walk(folder_path):
        for f in filenames:
            if f.lower().endswith(config.SUPPORTED_IMAGE_EXTENSIONS):
                file_id = os.path.splitext(f)[0]
                full_path = os.path.join(root, f)
                id_map[file_id].append(full_path)
    
    gt_pairs = []
    for file_id, paths in id_map.items():
        if len(paths) > 1:
            # Sort paths - assume first one is "original"
            paths.sort()
            original = paths[0]
            
            # Only pair original with each variant
            for variant in paths[1:]:
                gt_pairs.append(tuple(sorted((original, variant))))
    
    return gt_pairs

def is_original_file(filepath):
    
    return "original" in filepath.lower()

def calculate_wasted_space(duplicates, seen_files=None):
    
    if seen_files is None:
        seen_files = set()
    
    wasted_size_mb = 0
    
    for dup in duplicates:
        f1, f2 = dup['file1'], dup['file2']
        is_f1_orig = is_original_file(f1)
        is_f2_orig = is_original_file(f2)
        
        
        target_file = None
        if is_f1_orig and not is_f2_orig:
            target_file = f2
        elif is_f2_orig and not is_f1_orig:
            target_file = f1
        else:
            target_file = f2

        if target_file and target_file not in seen_files:
            try: 
                wasted_size_mb += os.path.getsize(target_file) / config.BYTES_TO_MB
                seen_files.add(target_file)
            except:
                pass
    
    return wasted_size_mb

def normalize_pair(pair):
   
    return tuple(sorted((os.path.basename(pair[0]), os.path.basename(pair[1]))))

def walk_image_files(folder):
    
    if not os.path.exists(folder):
        return
    
    for root, dirs, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(config.SUPPORTED_IMAGE_EXTENSIONS):
                yield os.path.join(root, f)


def identify_original_in_cluster(cluster):
    """Identify which file is the 'original' in a cluster"""
    scores = []
    
    for file_path in cluster:
        score = 0
        
        if "/original/" in file_path or "\\original\\" in file_path:
            score += 1000
        
        basename = os.path.basename(file_path).lower()
        if 'original' in basename:
            score += 500
        
        if any(kw in basename for kw in ['master', 'source', 'raw', 'hq']):
            score += 100
        
        try:
            img = Image.open(file_path)
            megapixels = (img.width * img.height) / 1_000_000
            score += megapixels * 10
        except:
            pass
        
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.png', '.tiff', '.bmp']:
            score += 50
        
        path_lower = file_path.lower()
        if 'jpeg' in path_lower:
            for comp in ['/3', '/5', '/8', '/10', '/15', '/20', '/30', '/50', '/75']:
                if comp in path_lower or comp.replace('/', '\\') in path_lower:
                    score -= 100
                    break
        
        scores.append({'path': file_path, 'score': score})
    
    scores.sort(key=lambda x: x['score'], reverse=True)
    return scores[0]['path']


def organize_clusters_with_originals(duplicates_list):
    """Organize duplicates: 1 original -> [all its unique duplicates with CORRECT similarity scores]"""
    import networkx as nx
    
    if not duplicates_list:
        return []
    
    # Build a complete score map for ALL pairs (both directions)
    score_map = {}
    for item in duplicates_list:
        f1, f2 = item['file1'], item['file2']
        score = item.get('score', 1.0)
        
        # Store in both directions
        score_map[(f1, f2)] = score
        score_map[(f2, f1)] = score
    
    # Build graph for clustering
    g = nx.Graph()
    for item in duplicates_list:
        g.add_edge(item['file1'], item['file2'])
    
    organized_clusters = []
    
    for component in nx.connected_components(g):
        if len(component) < 2:
            continue
        
        cluster_files = list(component)
        original = identify_original_in_cluster(cluster_files)
        duplicates = [f for f in cluster_files if f != original]
        
        duplicate_info = []
        
        for dup_file in duplicates:
            # Try to get direct score between original and duplicate
            score = score_map.get((original, dup_file))
            
            # If no direct edge exists, find the path and use minimum score
            if score is None:
                # Find shortest path in graph
                try:
                    path = nx.shortest_path(g, original, dup_file)
                    # Get minimum score along the path
                    path_scores = []
                    for i in range(len(path) - 1):
                        edge_score = score_map.get((path[i], path[i+1]), 0.5)
                        path_scores.append(edge_score)
                    score = min(path_scores) if path_scores else 0.8
                except:
                    score = 0.8  # Default if path finding fails
            
            duplicate_info.append({
                'path': dup_file,
                'score': score
            })
        
        # Sort duplicates by similarity score (highest first)
        duplicate_info.sort(key=lambda x: x['score'], reverse=True)
        
        organized_clusters.append({
            'original': original,
            'duplicates': duplicate_info,
            'total_count': len(cluster_files)
        })
    
    # Sort clusters by number of files (largest first)
    organized_clusters.sort(key=lambda x: x['total_count'], reverse=True)
    return organized_clusters


def auto_select_duplicates_for_deletion(organized_clusters):
    """Auto-mark all duplicates for deletion"""
    deletion_queue = set()
    for cluster in organized_clusters:
        for dup in cluster['duplicates']:
            deletion_queue.add(dup['path'])
    return deletion_queue