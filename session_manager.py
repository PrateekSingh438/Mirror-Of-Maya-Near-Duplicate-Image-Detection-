import streamlit as st
import os
import json
from datetime import datetime
import config

def initialize_session_state():
    defaults = {
        'detector': None,
        'duplicates': [],
        'all_duplicates': [],
        'ground_truth': [],
        'deletion_queue': set(),
        'f1_score': 0.0,
        'optimal_thresh': config.DEFAULT_THRESHOLD,
        'calibration_history': [],
        'current_slider_val': config.DEFAULT_THRESHOLD,
        'scan_stats': {},
        'selected_model': config.MODEL_ID,
        'page': 0,
        'clustering_mode': 'basename'
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def save_session_state():
    try:
        state_data = {
            'optimal_thresh': st.session_state.optimal_thresh,
            'f1_score': st.session_state.f1_score,
            'calibration_history': st.session_state.calibration_history,
            'deletion_queue': list(st.session_state.deletion_queue),
            'last_scan': datetime.now().isoformat(),
            'selected_model': st.session_state.get('selected_model', config.MODEL_ID),
            'clustering_mode': st.session_state.get('clustering_mode', 'basename')
        }
        with open('session_state.json', 'w') as f:
            json.dump(state_data, f)
    except Exception as e:
        st.warning(f"Could not save session: {str(e)}")

def load_session_state():
    try:
        if os.path.exists('session_state.json'):
            with open('session_state.json', 'r') as f:
                state_data = json.load(f)
                st.session_state.optimal_thresh = state_data.get('optimal_thresh', config.DEFAULT_THRESHOLD)
                st.session_state.f1_score = state_data.get('f1_score', 0.0)
                st.session_state.calibration_history = state_data.get('calibration_history', [])
                st.session_state.deletion_queue = set(state_data.get('deletion_queue', []))
                st.session_state.selected_model = state_data.get('selected_model', config.MODEL_ID)
                st.session_state.clustering_mode = state_data.get('clustering_mode', 'basename')
                return state_data.get('last_scan')
    except:
        pass
    return None

def recalculate_metrics(threshold):
    if not st.session_state.get('all_duplicates') or not st.session_state.get('ground_truth'):
        return 0.0, 0.0, 0.0
    
    from utils import normalize_pair_fullpath
    
    filtered = [d for d in st.session_state.all_duplicates if d['score'] >= threshold]
    det_set = set(normalize_pair_fullpath((d['file1'], d['file2'])) for d in filtered)
    gt_set = set(normalize_pair_fullpath(p) for p in st.session_state.ground_truth)
    
    tp = len(det_set.intersection(gt_set))
    fp = len(det_set - gt_set)
    fn = len(gt_set - det_set)
    
    prec = tp / (tp + fp + config.EPSILON) if (tp + fp) > 0 else 0
    rec = tp / (tp + fn + config.EPSILON) if (tp + fn) > 0 else 0
    f1 = 2 * (prec * rec) / (prec + rec + config.EPSILON) if (prec + rec) > 0 else 0
    
    return f1, prec, rec