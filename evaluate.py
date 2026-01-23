import os
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import precision_recall_curve, auc
import config
from data_loader import get_image_paths, create_data_loader, get_ground_truth_mapping
from utils import extract_embeddings
from engine import FeatureExtractor, SearchEngine

def run_evaluation_search(model_name, distance_metric, base_path=config.BASE_PATH):
    """
    Loads data, extracts features, runs the search, and returns raw results.
    Does NOT calculate final metrics based on a specific threshold.
    """
    # 1. Load Data
    image_paths = get_image_paths(base_path)
    if not image_paths:
        print("No images found in data directory.")
        return None, None, None

    # 2. Initialize Model and DataLoader
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    feature_extractor = FeatureExtractor(model_name)
    dataloader = create_data_loader(image_paths, model_name)

    # 3. Extract Embeddings
    print(f"Extracting embeddings using {model_name}...")
    embeddings, image_ids = extract_embeddings(feature_extractor, dataloader, device)

    # 4. Initialize Search Engine
    search_engine = SearchEngine(embeddings, image_ids, metric=distance_metric)

    # 5. Load ground truth
    ground_truth_mapping = get_ground_truth_mapping(base_path)
    query_ids = list(ground_truth_mapping.keys())

    if not query_ids:
        print("No ground truth query images found.")
        return None, None, None

    # 6. Perform search
    print(f"Performing search for {len(query_ids)} queries...")
    # matches is a list of tuples: (query_id, result_id, score)
    raw_matches = search_engine.batch_search(query_ids, top_k=config.TOP_K)

    return raw_matches, ground_truth_mapping, embeddings, image_ids

def calculate_metrics_at_threshold(matches_at_threshold, ground_truth_mapping):
    """
    Calculates Precision, Recall, and F1 for a given set of matches that
    have already been filtered by a threshold.
    """
    # Find true positives based on ground truth
    # A match is a true positive if it's in the ground truth set for the query
    true_positive_matches = [
        (q_id, r_id, score)
        for q_id, r_id, score in matches_at_threshold
        if q_id in ground_truth_mapping and r_id in ground_truth_mapping[q_id]
    ]

    true_positives = len(true_positive_matches)
    total_matches = len(matches_at_threshold)
    
    # Calculate total relevant pairs in ground truth (for recall denominator)
    total_relevant = sum(len(s) for s in ground_truth_mapping.values())

    if total_matches == 0:
        precision = 0.0
    else:
        precision = true_positives / total_matches

    if total_relevant == 0:
        recall = 0.0
    else:
        recall = true_positives / total_relevant

    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * (precision * recall) / (precision + recall)

    return precision, recall, f1, true_positive_matches

def filter_matches_by_threshold(raw_matches, distance_metric, threshold):
    """
    Filters the raw search results based on the given threshold and metric type.
    """
    filtered_matches = []
    similarity_metrics = ["cosine", "dot_product"]

    for q_id, r_id, score in raw_matches:
        if distance_metric in similarity_metrics:
            # For similarity, score must be >= threshold
            if score >= threshold:
                filtered_matches.append((q_id, r_id, score))
        else:
            # For distance, score must be <= threshold
            if score <= threshold:
                filtered_matches.append((q_id, r_id, score))
                
    return filtered_matches

def plot_pr_curve(raw_matches, ground_truth_mapping, distance_metric):
    """
    Plots the Precision-Recall curve based on the raw top-K matches.
    """
    y_true = []
    y_scores = []

    similarity_metrics = ["cosine", "dot_product"]
    is_similarity = distance_metric in similarity_metrics

    # Prepare data for sklearn's precision_recall_curve
    for q_id, r_id, score in raw_matches:
        # Determine if this match is a true positive according to ground truth
        is_relevant = (q_id in ground_truth_mapping and r_id in ground_truth_mapping[q_id])
        y_true.append(1 if is_relevant else 0)
        
        # For distance metrics, we need similarity-like scores for the PR curve function
        # (higher is better). We can negate distances.
        if is_similarity:
             y_scores.append(score)
        else:
             y_scores.append(-score) # Negate distance so lower distance becomes higher score

    if not y_true:
         return None

    precision, recall, _ = precision_recall_curve(y_true, y_scores)
    pr_auc = auc(recall, precision)

    fig, ax = plt.subplots()
    ax.plot(recall, precision, label=f'PR Curve (AUC = {pr_auc:.2f})')
    ax.set_xlabel('Recall')
    ax.set_ylabel('Precision')
    ax.set_title('Precision-Recall Curve (Top-K Candidates)')
    ax.legend(loc="lower left")
    ax.grid(True)
    
    return fig

import torch
# Ensure evaluate_model is still available for backward compatibility if needed, 
# but app.py will use the split functions above.
def evaluate_model(model_name, distance_metric, base_path=config.BASE_PATH):
     # This function is now a wrapper for the split logic, calculating metrics at a default threshold (e.g., 0.5 for cosine)
     raw_matches, ground_truth_mapping, _, _ = run_evaluation_search(model_name, distance_metric, base_path)
     
     similarity_metrics = ["cosine", "dot_product"]
     # Set a reasonable default threshold for initial calculation
     default_threshold = 0.5 if distance_metric in similarity_metrics else 10.0

     filtered_matches = filter_matches_by_threshold(raw_matches, distance_metric, default_threshold)
     precision, recall, f1, relevant_matches = calculate_metrics_at_threshold(filtered_matches, ground_truth_mapping)
     
     fig = plot_pr_curve(raw_matches, ground_truth_mapping, distance_metric)
     
     return {
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "matches": relevant_matches, # Returns matches at default threshold
        "pr_curve_plot": fig,
        "raw_matches": raw_matches, # keep raw for re-filtering
        "ground_truth": ground_truth_mapping
    }