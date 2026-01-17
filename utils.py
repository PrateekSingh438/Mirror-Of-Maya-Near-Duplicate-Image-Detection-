import os
from collections import defaultdict
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
            for i in range(len(paths)):
                for j in range(i + 1, len(paths)):
                    gt_pairs.append(tuple(sorted((paths[i], paths[j]))))
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