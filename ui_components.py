import streamlit as st
import os
import pandas as pd
from datetime import datetime
import config
from engine import DuplicateDetector
from utils import get_dir_size
from session_manager import save_session_state, recalculate_metrics

# -----------------------------
# SESSION STATE INITIALIZATION
# -----------------------------
if 'clustering_mode' not in st.session_state:
    st.session_state.clustering_mode = 'basename'

def apply_custom_css():
    """Apply custom CSS styling"""
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');
        
        .main {
            background: #0f0f23;
            background-image: 
                radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.15) 0px, transparent 50%),
                radial-gradient(at 100% 0%, rgba(168, 85, 247, 0.15) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(236, 72, 153, 0.15) 0px, transparent 50%);
            color: #e2e8f0;
        }
        
        .main::before {
            content: "";
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-image: 
                linear-gradient(rgba(99, 102, 241, 0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(99, 102, 241, 0.03) 1px, transparent 1px);
            background-size: 50px 50px;
            pointer-events: none;
            z-index: 0;
            animation: gridMove 20s linear infinite;
        }
        
        @keyframes gridMove {
            0% { transform: translate(0, 0); }
            100% { transform: translate(50px, 50px); }
        }
        
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
            border-right: 1px solid rgba(99, 102, 241, 0.2);
        }
        
        .main-header {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 4rem;
            font-weight: 800;
            text-align: center;
            background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
            letter-spacing: -2px;
        }
        
        .subtitle {
            font-family: 'Inter', sans-serif;
            font-size: 1.1rem;
            text-align: center;
            color: #94a3b8;
            margin-bottom: 3rem;
        }
        
        .similarity-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            border-radius: 50px;
            font-weight: 600;
            font-size: 0.875rem;
            font-family: 'Inter', sans-serif;
        }
        
        .similarity-high { 
            background: linear-gradient(135deg, rgba(16, 185, 129, 0.2) 0%, rgba(5, 150, 105, 0.2) 100%);
            color: #10b981;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }
        
        .similarity-medium { 
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.2) 0%, rgba(139, 92, 246, 0.2) 100%);
            color: #8b5cf6;
            border: 1px solid rgba(99, 102, 241, 0.3);
        }
        
        .similarity-low { 
            background: linear-gradient(135deg, rgba(239, 68, 68, 0.2) 0%, rgba(220, 38, 38, 0.2) 100%);
            color: #ef4444;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }
    </style>
    """, unsafe_allow_html=True)

def render_header():
    """Render main header"""
    st.markdown('<h1 class="main-header">MIRROR OF MAYA</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Near-Duplicate Image Detection System</p>', unsafe_allow_html=True)

def render_clustering_mode_selector():
    """Render clustering mode selector in sidebar"""
    with st.expander("🔀 Clustering Mode", expanded=True):
        mode = st.radio(
            "How should duplicates be grouped?",
            options=["basename", "semantic"],
            format_func=lambda x: {
                "basename": "🎯 Basename Match (Conservative)",
                "semantic": "🧠 Semantic Similarity (Aggressive)"
            }[x],
            index=0 if st.session_state.get('clustering_mode', 'basename') == 'basename' else 1
        )

        if mode != st.session_state.get('clustering_mode', 'basename'):
            st.session_state.clustering_mode = mode
            st.rerun()

        if mode == "basename":
            st.info("📌 Conservative: Only matching filenames shown")
        else:
            st.warning("⚠️ Aggressive: All visually similar images shown")

def render_sidebar():
    """Render sidebar with all controls"""
    with st.sidebar:
        st.markdown("### ⚙️ CONTROL CENTER")
        st.markdown("---")
        
        _render_model_selection()
        _render_dataset_config()
        render_clustering_mode_selector()
        _render_advanced_settings()
        
        st.markdown("---")
        st.markdown("### 🚀 ACTIONS")
        
        _render_scan_button()
        _render_session_info()

def _render_model_selection():
    """Render model selection in sidebar"""
    with st.expander("🤖 Model Selection", expanded=True):
        available_models = {
            "DINOv2 Small (Fast)": "facebook/dinov2-small",
            "DINOv2 Base (Balanced)": "facebook/dinov2-base",
            "DINOv2 Large (Accurate)": "facebook/dinov2-large"
        }
        
        selected_model_name = st.selectbox(
            "Vision Model",
            list(available_models.keys()),
            index=list(available_models.values()).index(st.session_state.selected_model)
        )
        st.session_state.selected_model = available_models[selected_model_name]
        
        if st.session_state.selected_model != config.MODEL_ID:
            st.info("⚠️ Model change requires re-scan")

def _render_dataset_config():
    """Render dataset configuration in sidebar"""
    with st.expander("📁 Dataset", expanded=True):
        dataset_path = st.text_input("Dataset Path", value=config.DATASET_PATH, key="dataset_path_input")
        
        if os.path.exists(dataset_path):
            dir_size = get_dir_size(dataset_path)
            st.success(f"✓ {dir_size:.1f} MB")
        else:
            st.error("❌ Not found")

def _render_advanced_settings():
    """Render advanced settings in sidebar"""
    with st.expander("🔧 Advanced", expanded=False):
        batch_size = st.slider("Batch Size", 8, 64, config.BATCH_SIZE, 8, key="batch_size_slider")

def _render_scan_button():
    """Render the main scan button"""
    if st.button("🔄 Full Scan", type="primary", use_container_width=True):
        dataset_path = st.session_state.get('dataset_path_input', config.DATASET_PATH)
        
        if not os.path.exists(dataset_path):
            st.error("Invalid path!")
        else:
            start_time = datetime.now()
            
            with st.spinner("Initializing..."):
                config.MODEL_ID = st.session_state.selected_model
                detector = DuplicateDetector()
            
            with st.spinner("Indexing..."):
                detector.bulk_index(dataset_path)
                st.session_state.detector = detector
            
            with st.spinner("Calibrating..."):
                thresh, f1, history, gt_pairs = detector.calibrate_threshold(dataset_path)
                st.session_state.optimal_thresh = thresh
                st.session_state.f1_score = f1
                st.session_state.calibration_history = history
                st.session_state.current_slider_val = thresh
                st.session_state.ground_truth = gt_pairs
            
            with st.spinner("Finding duplicates..."):
                min_thresh = min(config.CALIBRATION_THRESHOLDS)
                all_dups = detector.find_duplicates(threshold=min_thresh)
                st.session_state.all_duplicates = all_dups

                filtered = [d for d in all_dups if d['score'] >= thresh]

                if st.session_state.clustering_mode == "basename":
                    filtered = [
                        d for d in filtered
                        if os.path.basename(d['file1']) == os.path.basename(d['file2'])
                    ]

                st.session_state.duplicates = filtered
            
            scan_time = (datetime.now() - start_time).total_seconds()
            st.session_state.scan_stats = {
                'total_images': detector.index.ntotal,
                'scan_time': scan_time,
                'duplicates_found': len(st.session_state.duplicates),
                'timestamp': datetime.now().isoformat()
            }
            
            save_session_state()
            st.success(f"✓ Complete! F1: {f1:.4f}")
            st.rerun()

def _render_session_info():
    """Render session information in sidebar"""
    st.markdown("---")
    st.markdown("### 📊 Session Info")
    
    if st.session_state.get('scan_stats'):
        stats = st.session_state.scan_stats
        st.metric("Images Indexed", f"{stats['total_images']:,}")
        st.metric("Scan Time", f"{stats['scan_time']:.1f}s")
        st.metric("Duplicates Found", f"{stats['duplicates_found']:,}")
        
        if 'timestamp' in stats:
            timestamp = datetime.fromisoformat(stats['timestamp'])
            st.caption(f"Last scan: {timestamp.strftime('%Y-%m-%d %H:%M')}")
    else:
        st.info("No scan performed yet")

def render_threshold_control():
    """Render dynamic threshold control"""
    st.markdown("### 🎚️ Dynamic Threshold Control")
    
    col_slider, col_metrics = st.columns([2, 2])
    
    with col_slider:
        new_thresh = st.slider(
            "Similarity Threshold",
            min_value=0.60,
            max_value=0.99,
            value=st.session_state.current_slider_val,
            step=0.01,
            key="dynamic_threshold"
        )
        
        if new_thresh != st.session_state.current_slider_val:
            st.session_state.current_slider_val = new_thresh
            f1, prec, rec = recalculate_metrics(new_thresh)

            filtered = [
                d for d in st.session_state.all_duplicates
                if d['score'] >= new_thresh
            ]

            if st.session_state.clustering_mode == "basename":
                filtered = [
                    d for d in filtered
                    if os.path.basename(d['file1']) == os.path.basename(d['file2'])
                ]

            st.session_state.duplicates = filtered
    
    with col_metrics:
        f1, prec, rec = recalculate_metrics(st.session_state.current_slider_val)
        
        mcol1, mcol2, mcol3 = st.columns(3)
        mcol1.metric("F1", f"{f1:.3f}")
        mcol2.metric("Precision", f"{prec:.3f}")
        mcol3.metric("Recall", f"{rec:.3f}")
    
    st.markdown("---")

def get_short_path(path):
    """Get shortened path for display"""
    try:
        if not path: 
            return ""
        parent = os.path.basename(os.path.dirname(path))
        filename = os.path.basename(path)
        return f"{parent}/{filename}"
    except:
        return os.path.basename(path)

def get_similarity_class(score):
    """Get CSS class based on similarity score"""
    if score >= 0.90:
        return "similarity-high"
    elif score >= 0.75:
        return "similarity-medium"
    return "similarity-low"