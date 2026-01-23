import os
import numpy as np
from engine import DuplicateDetector
from utils import get_image_files
import config

os.environ["KMP_DUPLICATE_LIB_OK"] = config.ENV_KMP_DUPLICATE_LIB if hasattr(config, 'ENV_KMP_DUPLICATE_LIB') else "TRUE"

def get_attack_folders():
    """Get all attack category folders"""
    folders = {}
    
    # Standard attacks
    if hasattr(config, 'ATTACK_CATEGORIES'):
        for name, rel_path in config.ATTACK_CATEGORIES.items():
            folders[name] = os.path.join(config.DATASET_PATH, rel_path)
    
    # Crop attacks
    if hasattr(config, 'CROP_CATEGORIES') and hasattr(config, 'CROPS_PATH'):
        for name, rel_path in config.CROP_CATEGORIES.items():
            folders[name] = os.path.join(config.CROPS_PATH, rel_path)
    
    return folders

def evaluate_category(detector, category_name, folder_path):
    """Evaluate detection on one attack category"""
    if not os.path.exists(folder_path):
        return None, "Folder not found"

    query_files = get_image_files(folder_path)
    if not query_files:
        return None, "No images found"

    tp = 0
    scores = []
    threshold = getattr(config, 'BENCHMARK_THRESHOLD', 0.75)

    for q_path in query_files:
        q_id = os.path.splitext(os.path.basename(q_path))[0]
        results = detector.find_matches_for_file(q_path, threshold=threshold)
        
        found = False
        for res in results:
            res_id = os.path.splitext(os.path.basename(res['path']))[0]
            scores.append(res['score'])
            if res_id == q_id:
                found = True
                break
        
        if found:
            tp += 1
    
    recall = tp / len(query_files) if query_files else 0
    avg_score = np.mean(scores) if scores else 0
    
    return {
        "recall": recall,
        "avg_score": avg_score,
        "true_positives": tp,
        "total_queries": len(query_files)
    }, None

def get_status(recall):
    """Get status label for recall"""
    excellent_thresh = getattr(config, 'EXCELLENT_RECALL_THRESHOLD', 0.90)
    weak_thresh = getattr(config, 'WEAK_RECALL_THRESHOLD', 0.70)
    
    if recall > excellent_thresh:
        return "EXCELLENT"
    elif recall < weak_thresh:
        return "WEAK"
    return "GOOD"

def print_benchmark_header():
    """Print benchmark table header"""
    print("\n" + "="*65)
    print(f"{'ATTACK CATEGORY':<20} | {'RECALL':<10} | {'AVG SCORE':<10} | {'STATUS'}")
    print("="*65)

def print_benchmark_result(name, result, error):
    """Print single benchmark result"""
    if error:
        print(f"{name:<20} | {'SKIPPED':<10} | {'N/A':<10} | {error}")
    else:
        status = get_status(result['recall'])
        print(f"{name:<20} | {result['recall']:.4f}    | {result['avg_score']:.4f}    | {status}")

def run_comprehensive_benchmark():
    """Run benchmark on all attack categories"""
    print("Initializing Benchmark...")
    detector = DuplicateDetector()
    
    original_dir = os.path.join(config.DATASET_PATH, config.ORIGINAL_DIR_NAME)
    print(f"Indexing originals from {original_dir}...")
    detector.bulk_index(original_dir)
    
    print_benchmark_header()

    total_tp = 0
    total_queries = 0
    attack_folders = get_attack_folders()

    for name, folder in attack_folders.items():
        result, error = evaluate_category(detector, name, folder)
        print_benchmark_result(name, result, error)
        
        if result:
            total_tp += result['true_positives']
            total_queries += result['total_queries']

    final_recall = total_tp / total_queries if total_queries > 0 else 0
    print("="*65)
    print(f"FINAL SYSTEM RECALL: {final_recall:.4f}")
    print("="*65)

if __name__ == "__main__":
    run_comprehensive_benchmark()