import os
import time
from engine import DuplicateDetector
from evaluate import calculate_metrics

def find_optimal_threshold(detector, ground_truth_pairs):
    import numpy as np

    print("\nOPTIMIZING THRESHOLD...")
    print(f"{'THRESHOLD':<10} | {'F1 SCORE':<10} | {'RECALL':<10} | {'PRECISION':<10}")
    print("-" * 50)

    best_f1 = 0
    best_thresh = 0

    for t in np.arange(0.80, 0.97, 0.02):
        preds = detector.find_duplicates(threshold=t)
        pred_pairs = [(p['file1'], p['file2']) for p in preds]

        tp = 0
        gt_set = set(ground_truth_pairs)
        for p in pred_pairs:
            if tuple(sorted(p)) in gt_set:
                tp += 1

        precision = tp / len(pred_pairs) if pred_pairs else 0
        recall = tp / len(ground_truth_pairs) if ground_truth_pairs else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        print(f"{t:.2f}       | {f1:.4f}     | {recall:.4f}     | {precision:.4f}")

        if f1 > best_f1:
            best_f1 = f1
            best_thresh = t

    print("-" * 50)
    print(f"BEST THRESHOLD: {best_thresh:.2f} (F1: {best_f1:.4f})")
    return best_thresh

DATASET_ROOT = "./dataset_copydays"
ORIGINAL_DIR = os.path.join(DATASET_ROOT, "original")
ATTACK_DIRS = {
    "Strong Attack": os.path.join(DATASET_ROOT, "strong"),
    "JPEG (Quality 3)": os.path.join(DATASET_ROOT, "jpeg", "3"),
    "JPEG (Quality 10)": os.path.join(DATASET_ROOT, "jpeg", "10"),
}

def get_files_in_dir(directory):
    files = []
    if not os.path.exists(directory):
        return []
    for f in os.listdir(directory):
        if f.lower().endswith(('.jpg', '.jpeg', '.png')):
            files.append(os.path.join(directory, f))
    return files

def run_benchmark():
    print("Starting Copydays Benchmark...")

    detector = DuplicateDetector()
    detector.bulk_index(DATASET_ROOT)

    print("\n" + "="*50)
    print(f"{'CATEGORY':<25} | {'PRECISION':<10} | {'RECALL':<10} | {'F1 SCORE':<10}")
    print("="*50)

    for category_name, attack_dir in ATTACK_DIRS.items():
        if not os.path.exists(attack_dir):
            print(f"{category_name:<25} | {'SKIPPED (Not Found)':<30}")
            continue

        gt_pairs = []
        attack_files = get_files_in_dir(attack_dir)
        original_files = get_files_in_dir(ORIGINAL_DIR)

        orig_map = {os.path.splitext(os.path.basename(f))[0]: f for f in original_files}

        for af in attack_files:
            af_id = os.path.splitext(os.path.basename(af))[0]
            if af_id in orig_map:
                gt_pairs.append(tuple(sorted((orig_map[af_id], af))))

        all_preds = detector.find_duplicates(threshold=0.88)

        category_preds = []
        for p in all_preds:
            if attack_dir in os.path.dirname(p['file1']) or attack_dir in os.path.dirname(p['file2']):
                category_preds.append((p['file1'], p['file2']))

        tp = 0
        gt_set = set(gt_pairs)
        for p in category_preds:
            if tuple(sorted(p)) in gt_set:
                tp += 1

        precision = tp / len(category_preds) if category_preds else 0
        recall = tp / len(gt_pairs) if gt_pairs else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        print(f"{category_name:<25} | {precision:.4f}     | {recall:.4f}     | {f1:.4f}")

    print("="*50)

if __name__ == "__main__":
    run_benchmark()
