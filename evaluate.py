from sklearn.metrics import f1_score, precision_score, recall_score

def calculate_metrics(detected_pairs, ground_truth_pairs):
    def normalize_pair(p):
        import os
        return tuple(sorted((os.path.basename(p[0]), os.path.basename(p[1]))))

    detected_set = set(normalize_pair(p) for p in detected_pairs)
    truth_set = set(normalize_pair(p) for p in ground_truth_pairs)

    true_positives = len(detected_set.intersection(truth_set))
    false_positives = len(detected_set - truth_set)
    false_negatives = len(truth_set - detected_set)

    precision = true_positives / (true_positives + false_positives + 1e-9)
    recall = true_positives / (true_positives + false_negatives + 1e-9)
    f1 = 2 * (precision * recall) / (precision + recall + 1e-9)

    print("\n--- FINAL EVALUATION REPORT ---")
    print(f"True Positives:  {true_positives}")
    print(f"False Positives: {false_positives}")
    print(f"Missed (FN):     {false_negatives}")
    print(f"F1 Score:        {f1:.4f}")
    print("-----------------------------------")

    return f1
