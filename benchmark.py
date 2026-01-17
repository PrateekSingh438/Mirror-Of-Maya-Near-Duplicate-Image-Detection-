import os
import numpy as np
from engine import DuplicateDetector
from utils import get_image_files
import config

os.environ["KMP_DUPLICATE_LIB_OK"] = config.ENV_KMP_DUPLICATE_LIB

def get_attack_folders():
 
    return {
        name: os.path.join(config.DATASET_PATH, relative_path)
        for name, relative_path in config.ATTACK_CATEGORIES.items()
    }

def evaluate_category(detector, category_name, folder_path):
   
    if not os.path.exists(folder_path):
        return None, "Folder not found"

    query_files = get_image_files(folder_path)
    if not query_files:
        return None, "No images found"

    tp = 0
    scores = []

    for q_path in query_files:
        q_id = os.path.splitext(os.path.basename(q_path))[0]
        results = detector.find_matches_for_file(q_path, threshold=config.BENCHMARK_THRESHOLD)
        
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
    
    if recall > config.EXCELLENT_RECALL_THRESHOLD:
        return "EXCELLENT"
    elif recall < config.WEAK_RECALL_THRESHOLD:
        return "WEAK"
    return "GOOD"

def print_benchmark_header():
    
    print("\n" + "="*65)
    print(f"{'ATTACK CATEGORY':<20} | {'RECALL':<10} | {'AVG SCORE':<10} | {'STATUS'}")
    print("="*65)

def print_benchmark_result(name, result, error):
   
    if error:
        print(f"{name:<20} | {'SKIPPED':<10} | {'N/A':<10} | {error}")
    else:
        status = get_status(result['recall'])
        print(f"{name:<20} | {result['recall']:.4f}    | {result['avg_score']:.4f}    | {status}")

def run_comprehensive_benchmark():
    
    print("Initializing Robust Benchmark...")
    detector = DuplicateDetector()
    
    original_dir = os.path.join(config.DATASET_PATH, config.ORIGINAL_DIR_NAME)
    print(f"Indexing Originals from {original_dir}...")
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