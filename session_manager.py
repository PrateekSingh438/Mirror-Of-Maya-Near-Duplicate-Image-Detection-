import streamlit as st
import os
import json
import uuid
from datetime import datetime

import config
from utils import duplicates_to_pairset, pair_metrics, filter_at_threshold

SESSION_FILE = os.path.join(config.TEMP_DIR, "session_state.json")


def is_running_locally():
    """True when the app runs on this machine (local paths and persisted
    preferences make sense)."""
    try:
        host = st.context.headers.get("Host", "")
        return "localhost" in host or "127.0.0.1" in host
    except Exception:
        return os.path.exists(config.DATASET_PATH)


def initialize_session_state():
    defaults = {
        'detector': None,
        'duplicates': [],            # pairs shown at the current threshold
        'all_duplicates': [],        # every candidate pair found by the scan
        'gt_groups': None,           # ground truth (None when unavailable)
        'gt_pairs': None,
        'eval_summary': None,        # calibration result dict from the engine
        'calibration_history': [],
        'deletion_queue': set(),     # session-only, never persisted
        'last_deletion': None,       # undo payload for the most recent delete
        'optimal_thresh': config.DEFAULT_THRESHOLD,
        'current_slider_val': config.DEFAULT_THRESHOLD,
        'scan_stats': {},
        'selected_model': config.DEFAULT_MODEL_ID,
        'page': 0,
        'hash_page': 0,
        'selection_gen': 0,          # bumped to reset the manager checkboxes
        'session_uid': uuid.uuid4().hex[:12],
        'active_dataset_path': None,
        'demo_mode': False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def save_session_state():
    """Persist harmless preferences only. The deletion queue is deliberately
    NOT saved: restoring it across sessions made one click delete files that
    were selected weeks earlier.

    Local runs only: on a hosted deployment every visitor shares the container
    filesystem, so persisting would leak one user's choices to the next."""
    if not is_running_locally():
        return
    try:
        state_data = {
            'optimal_thresh': st.session_state.optimal_thresh,
            'selected_model': st.session_state.get('selected_model', config.DEFAULT_MODEL_ID),
            'last_scan': datetime.now().isoformat(),
        }
        with open(SESSION_FILE, 'w') as f:
            json.dump(state_data, f)
    except Exception as e:
        st.warning(f"Could not save session: {e}")


def load_session_state():
    if not is_running_locally():
        return None
    try:
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, 'r') as f:
                state_data = json.load(f)
            st.session_state.optimal_thresh = state_data.get('optimal_thresh', config.DEFAULT_THRESHOLD)
            st.session_state.selected_model = state_data.get('selected_model', config.DEFAULT_MODEL_ID)
            return state_data.get('last_scan')
    except Exception:
        pass
    return None


def recalculate_metrics(threshold):
    """Pair-level precision/recall/F1 at `threshold`, full paths, full GT.
    Returns None when the dataset has no ground truth."""
    gt_pairs = st.session_state.get('gt_pairs')
    if not gt_pairs:
        return None

    filtered = filter_at_threshold(st.session_state.all_duplicates, threshold)
    det = duplicates_to_pairset(filtered)
    return pair_metrics(det, gt_pairs)
