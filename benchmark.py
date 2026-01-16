import os
import time
import numpy as np
from engine import DuplicateDetector

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

DATASET_ROOT = "./dataset_copydays"
ORIGINAL_DIR = os.path.join(DATASET_ROOT, "original")

ATTACK_CATEGORIES = {
    "JPEG 3": os.path.join(DATASET_ROOT, "jpeg", "3"),
    "JPEG 5": os.path.join(DATASET_ROOT, "jpeg", "5"),
    "JPEG 8": os.path.join(DATASET_ROOT, "jpeg", "8"),
    "JPEG 10": os.path.join(DATASET_ROOT, "jpeg", "10"),
    "JPEG 15": os.path.join(DATASET_ROOT, "jpeg", "15"),
    "JPEG 20": os.path.join(DATASET_ROOT, "jpeg", "20"),
    "JPEG 30": os.path.join(DATASET_ROOT, "jpeg", "30"),
    "JPEG 50": os.path.join(DATASET_ROOT, "jpeg", "50"),
    "JPEG 75": os.path.join(DATASET_ROOT, "jpeg", "75"),
    "Strong": os.path.join(DATASET_ROOT, "strong"),
}

TEST_THRESHOLD = 0.80 

def get_image_files(directory):
    if not os.path.exists(directory):
        return []
    return [os.path.join(directory, f) for f in os.listdir(directory) 
            if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

def run_comprehensive_benchmark():
    print("Initializing Robust Benchmark...")
    detector = DuplicateDetector()
    
    print(f"Indexing Originals from {ORIGINAL_DIR}...")
    detector.bulk_index(ORIGINAL_DIR)
    
    print("\n" + "="*65)
    print(f"{'ATTACK CATEGORY':<20} | {'RECALL':<10} | {'AVG SCORE':<10} | {'STATUS'}")
    print("="*65)

    total_tp = 0
    total_queries = 0

    for name, folder in ATTACK_CATEGORIES.items():
        if not os.path.exists(folder):
            print(f"{name:<20} | {'SKIPPED':<10} | {'N/A':<10} | Folder not found")
            continue

        query_files = get_image_files(folder)
        if not query_files:
            continue

        tp = 0
        scores = []

        for q_path in query_files:
            q_id = os.path.splitext(os.path.basename(q_path))[0]
            
            results = detector.find_matches_for_file(q_path, threshold=TEST_THRESHOLD)
            
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
        avg_s = np.mean(scores) if scores else 0
        
        status = "EXCELLENT" if recall > 0.9 else "WEAK" if recall < 0.5 else "GOOD"
        print(f"{name:<20} | {recall:.4f}    | {avg_s:.4f}    | {status}")
        
        total_tp += tp
        total_queries += len(query_files)

    final_recall = total_tp / total_queries if total_queries > 0 else 0
    print("="*65)
    print(f"FINAL SYSTEM RECALL: {final_recall:.4f}")
    print("="*65)

if __name__ == "__main__":
    run_comprehensive_benchmark()
