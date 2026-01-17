import config
from utils import normalize_pair, is_original_file

def calculate_metrics(detected_pairs, ground_truth_pairs):
    
    detected_set = set(normalize_pair(p) for p in detected_pairs)
    truth_set = set(normalize_pair(p) for p in ground_truth_pairs)

    true_positives = len(detected_set.intersection(truth_set))
    false_positives = len(detected_set - truth_set)
    false_negatives = len(truth_set - detected_set)

    precision = true_positives / (true_positives + false_positives + config.EPSILON)
    recall = true_positives / (true_positives + false_negatives + config.EPSILON)
    f1 = 2 * (precision * recall) / (precision + recall + config.EPSILON)

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
        f1, f2 = pair['file1'], pair['file2']
        
        f1_is_orig = is_original_file(f1)
        f2_is_orig = is_original_file(f2)
        
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