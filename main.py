import os
from engine import DuplicateDetector
from evaluate import calculate_metrics
import config

def main():
    
    detector = DuplicateDetector()
    detector.bulk_index(config.DATASET_PATH)
    raw_results = detector.find_duplicates()

    print(f"\nFound {len(raw_results)} potential duplicate pairs:")
    detected_pairs = []
    
    for r in raw_results:
        print(f"Match: {os.path.basename(r['file1'])} <-> {os.path.basename(r['file2'])} (Score: {r['score']:.4f})")
        detected_pairs.append((r["file1"], r["file2"]))

    
    ground_truth = [
        ("image_01.jpg", "image_01_crop.jpg")
    ]

    if len(detected_pairs) > 0 and len(ground_truth) > 0:
        f1_score = calculate_metrics(detected_pairs, ground_truth)
        print(f"\nF1 Score: {f1_score:.4f}")
    else:
        print("\nEvaluation skipped - no pairs to evaluate")

if __name__ == "__main__":
    main()