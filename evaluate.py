from sklearn.metrics import f1_score, precision_score, recall_score
import os

def calculate_metrics(detected_pairs, ground_truth_pairs):
    def normalize_pair(p):
        return tuple(sorted((os.path.basename(p[0]), os.path.basename(p[1]))))

    detected_set = set(normalize_pair(p) for p in detected_pairs)
    truth_set = set(normalize_pair(p) for p in ground_truth_pairs)

    true_positives = len(detected_set.intersection(truth_set))
    false_positives = len(detected_set - truth_set)
    false_negatives = len(truth_set - detected_set)

    precision = true_positives / (true_positives + false_positives + 1e-9)
    recall = true_positives / (true_positives + false_negatives + 1e-9)
    f1 = 2 * (precision * recall) / (precision + recall + 1e-9)

    return f1

def analyze_match_types(detected_pairs):
    orig_recovered = 0
    junk_to_junk = 0
    total = len(detected_pairs)
    
    if total == 0:
        return {
            "recovery": 0, 
            "cross": 0, 
            "total": 0,
            "recovery_pct": 0,
            "cross_pct": 0
        }

    for pair in detected_pairs:
        f1, f2 = pair['file1'].lower(), pair['file2'].lower()
        
        f1_is_orig = "original" in f1
        f2_is_orig = "original" in f2
        
        if f1_is_orig != f2_is_orig: 
            orig_recovered += 1
        elif not f1_is_orig and not f2_is_orig:
            junk_to_junk += 1

    return {
        "recovery": orig_recovered,
        "cross": junk_to_junk,
        "total": total,
        "recovery_pct": (orig_recovered / total) * 100,
        "cross_pct": (junk_to_junk / total) * 100
    }