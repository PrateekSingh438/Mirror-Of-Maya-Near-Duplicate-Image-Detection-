import streamlit as st
import os
from datetime import datetime
import config
from engine import DuplicateDetector
from utils import get_dir_size
from session_manager import save_session_state, recalculate_metrics



def apply_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700;900&family=Inter:wght@300;400;500;600;700;800&display=swap');
        
        /* Main container - Deep mystical background */
        .main {
            background: #0a0a1a;
            background-image: 
                radial-gradient(at 20% 30%, rgba(139, 92, 246, 0.15) 0px, transparent 50%),
                radial-gradient(at 80% 0%, rgba(168, 85, 247, 0.12) 0px, transparent 50%),
                radial-gradient(at 60% 100%, rgba(236, 72, 153, 0.12) 0px, transparent 50%),
                radial-gradient(at 0% 70%, rgba(16, 185, 129, 0.08) 0px, transparent 50%);
            color: #e2e8f0;
            position: relative;
        }
        
        /* Animated chakra pattern overlay */
        .main::before {
            content: "";
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-image: 
                repeating-conic-gradient(from 0deg at 50% 50%, 
                    transparent 0deg, 
                    rgba(139, 92, 246, 0.02) 15deg, 
                    transparent 30deg);
            pointer-events: none;
            z-index: 0;
            animation: rotateChakra 60s linear infinite;
        }
        
        @keyframes rotateChakra {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        
        /* Sidebar - Temple aesthetic */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1a1a3e 0%, #0f0f2e 100%);
            border-right: 2px solid rgba(139, 92, 246, 0.3);
            box-shadow: 5px 0 30px rgba(139, 92, 246, 0.2);
        }
        
        
        @keyframes pulse {
            0%, 100% { opacity: 0.3; transform: translateX(-50%) scale(1); }
            50% { opacity: 0.6; transform: translateX(-50%) scale(1.1); }
        }
        
        /* Main header - Divine title */
        .main-header {
            font-family: 'Cinzel', serif;
            font-size: 4.5rem;
            font-weight: 900;
            text-align: center;
            background: linear-gradient(135deg, 
                #6366f1 0%, 
                #a855f7 25%, 
                #ec4899 50%, 
                #f59e0b 75%, 
                #10b981 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-size: 200% auto;
            animation: shimmer 8s ease-in-out infinite;
            margin-bottom: 0.5rem;
            letter-spacing: 0.1em;
            text-shadow: 0 0 30px rgba(168, 85, 247, 0.5);
        }
        
        @keyframes shimmer {
            0%, 100% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
        }
        
        .subtitle {
            font-family: 'Cinzel', serif;
            font-size: 1.2rem;
            text-align: center;
            color: #a78bfa;
            margin-bottom: 3rem;
            letter-spacing: 0.15em;
            text-transform: uppercase;
            font-weight: 600;
        }
        
        /* Similarity badges - Mystical gems */
        .similarity-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.6rem 1.2rem;
            border-radius: 50px;
            font-weight: 700;
            font-size: 0.875rem;
            font-family: 'Cinzel', serif;
            letter-spacing: 0.05em;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        }
        
        .similarity-high { 
            background: linear-gradient(135deg, rgba(16, 185, 129, 0.3) 0%, rgba(5, 150, 105, 0.3) 100%);
            color: #10b981;
            border: 2px solid #10b981;
            box-shadow: 0 0 20px rgba(16, 185, 129, 0.4);
        }
        
        .similarity-medium { 
            background: linear-gradient(135deg, rgba(168, 85, 247, 0.3) 0%, rgba(139, 92, 246, 0.3) 100%);
            color: #a855f7;
            border: 2px solid #a855f7;
            box-shadow: 0 0 20px rgba(168, 85, 247, 0.4);
        }
        
        .similarity-low { 
            background: linear-gradient(135deg, rgba(239, 68, 68, 0.3) 0%, rgba(220, 38, 38, 0.3) 100%);
            color: #ef4444;
            border: 2px solid #ef4444;
            box-shadow: 0 0 20px rgba(239, 68, 68, 0.4);
        }
        
        /* Buttons - Sacred interface */
        .stButton > button {
            background: linear-gradient(135deg, #6366f1, #a855f7);
            border: 2px solid rgba(168, 85, 247, 0.5);
            color: white;
            font-family: 'Cinzel', serif;
            font-weight: 600;
            letter-spacing: 0.05em;
            border-radius: 10px;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 25px rgba(99, 102, 241, 0.5);
            border-color: rgba(168, 85, 247, 0.8);
        }
        
        /* Metrics - Divine indicators */
        [data-testid="stMetricValue"] {
            font-family: 'Cinzel', serif;
            font-weight: 700;
            background: linear-gradient(135deg, #6366f1, #a855f7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        /* Tabs - Sacred scrolls */
        .stTabs [data-baseweb="tab-list"] {
            gap: 1rem;
            background: rgba(26, 26, 62, 0.5);
            border-radius: 10px;
            padding: 0.5rem;
        }
        
        .stTabs [data-baseweb="tab"] {
            font-family: 'Cinzel', serif;
            font-weight: 600;
            letter-spacing: 0.05em;
            color: #94a3b8;
            border-radius: 8px;
            padding: 0.75rem 1.5rem;
            transition: all 0.3s ease;
        }
        
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(168, 85, 247, 0.2));
            color: #a855f7;
            border: 2px solid rgba(168, 85, 247, 0.5);
            box-shadow: 0 0 20px rgba(168, 85, 247, 0.3);
        }
        
        /* Expander - Mystical containers */
        .streamlit-expanderHeader {
            font-family: 'Cinzel', serif;
            font-weight: 600;
            color: #a855f7;
            background: rgba(139, 92, 246, 0.1);
            border-radius: 8px;
            border-left: 4px solid #a855f7;
        }
        
        /* Dataframes - Sacred scrolls */
        .dataframe {
            font-family: 'Inter', sans-serif;
            background: rgba(15, 15, 35, 0.6) !important;
            border: 1px solid rgba(139, 92, 246, 0.3);
            border-radius: 8px;
        }
        
        /* Success/Info/Warning messages - Divine messages */
        .stSuccess {
            background: linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(5, 150, 105, 0.15));
            border-left: 4px solid #10b981;
            font-family: 'Inter', sans-serif;
        }
        
        .stInfo {
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(139, 92, 246, 0.15));
            border-left: 4px solid #6366f1;
        }
        
        .stWarning {
            background: linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(251, 191, 36, 0.15));
            border-left: 4px solid #f59e0b;
        }
        
        /* Scrollbar - Chakra themed */
        ::-webkit-scrollbar {
            width: 12px;
            background: rgba(15, 15, 35, 0.8);
        }
        
        ::-webkit-scrollbar-thumb {
            background: linear-gradient(180deg, #6366f1, #a855f7);
            border-radius: 10px;
            border: 2px solid rgba(15, 15, 35, 0.8);
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: linear-gradient(180deg, #818cf8, #c084fc);
        }
    </style>
    """, unsafe_allow_html=True)

def render_header():
    st.markdown('''
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1 class="main-header">MIRROR OF MAYA</h1>
        <p class="subtitle">Where Illusions Reveal Truth</p>
        <div style="color: #64748b; font-style: italic; font-size: 0.9rem; max-width: 800px; margin: 0 auto; line-height: 1.6;">
            Just as Maya weaves illusions where one truth manifests in countless forms, 
            the digital realm births infinite avatars from single souls. 
            The Mirror of Maya pierces this veil, revealing the original essence beneath layers of transformation.
        </div>
    </div>
    ''', unsafe_allow_html=True)



def render_sidebar():
    with st.sidebar:
        st.markdown("### CONTROLS")
        st.markdown("---")
        
        _render_model_selection()
        _render_dataset_config()
        
        st.markdown("---")
        st.markdown("### SACRED ACTIONS")
        
        _render_scan_button()
        _render_session_info()

def _render_model_selection():
    with st.expander("MODEL SELECTION", expanded=True):
        available_models = {
            "DINOv2 Small (21M paramaters)": "facebook/dinov2-small",
            "DINOv2 Base (86M parameters)": "facebook/dinov2-base",
            "DINOv2 Large (300M parameters)": "facebook/dinov2-large"
        }
        
        selected_model_name = st.selectbox(
            "Model Power Level:",
            list(available_models.keys()),
            index=list(available_models.values()).index(st.session_state.selected_model)
        )
        st.session_state.selected_model = available_models[selected_model_name]
        
        if st.session_state.selected_model != config.MODEL_ID:
            st.info("Model change requires re-consecration (re-scan)")

def _render_dataset_config():
    with st.expander("Sacred Repository", expanded=True):
        dataset_path = st.text_input("Repository Path:", value=config.DATASET_PATH, key="dataset_path_input")
        
        if os.path.exists(dataset_path):
            dir_size = get_dir_size(dataset_path)
            st.success(f"✓ {dir_size:.1f} MB of digital souls indexed")
        else:
            st.error("Repository not found in this realm")

def _render_scan_button():
    if st.button("SCAN DATABASE", type="primary", width='stretch'):
        dataset_path = st.session_state.get('dataset_path_input', config.DATASET_PATH)
        
        if not os.path.exists(dataset_path):
            st.error("Sacred path not found!")
        else:
            start_time = datetime.now()
            
            with st.spinner("Summoning the Model..."):
                config.MODEL_ID = st.session_state.selected_model
                detector = DuplicateDetector()
            
            with st.spinner("Scanning database..."):
                detector.bulk_index(dataset_path)
                st.session_state.detector = detector
            
            with st.spinner("Calibrating divine discernment..."):
                thresh, f1, history, gt_pairs = detector.calibrate_threshold(dataset_path)
                st.session_state.optimal_thresh = thresh
                st.session_state.f1_score = f1
                st.session_state.calibration_history = history
                st.session_state.current_slider_val = thresh
                st.session_state.ground_truth = gt_pairs
            
            with st.spinner("Piercing the veil of illusions..."):
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
            st.success(f"Divine revelation complete! Discernment: {f1:.1%}")
            st.rerun()

def _render_session_info():
    st.markdown("---")
    st.markdown("###Scan Statistics")
    
    if st.session_state.get('scan_stats'):
        stats = st.session_state.scan_stats
        st.metric("Souls Indexed", f"{stats['total_images']:,}")
        st.metric("Revelation Time", f"{stats['scan_time']:.1f}s")
        st.metric("Illusions Found", f"{stats['duplicates_found']:,}")
        
        if 'timestamp' in stats:
            timestamp = datetime.fromisoformat(stats['timestamp'])
            st.caption(f"Last invocation: {timestamp.strftime('%Y-%m-%d %H:%M')}")
    else:
        st.info("Awaiting first scan")

def render_threshold_control():
    st.markdown("### Chakra Precision Control")
    st.markdown("*Adjust the sharpness of divine discernment*")
    
    col_slider, col_metrics = st.columns([2, 2])
    
    with col_slider:
        new_thresh = st.slider(
            "Discernment Threshold:",
            min_value=config.MIN_THRESHOLD,
            max_value=config.MAX_THRESHOLD,
            value=st.session_state.current_slider_val,
            step=0.01,
            key="dynamic_threshold",
            help="Higher = stricter (fewer false positives), Lower = lenient (fewer false negatives)"
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
        mcol1.metric("F1", f"{f1:.1%}")
        mcol2.metric("Precision", f"{prec:.1%}")
        mcol3.metric("Recall", f"{rec:.1%}")
    
    st.markdown("---")

def get_short_path(path):
    try:
        if not path: 
            return ""
        parent = os.path.basename(os.path.dirname(path))
        filename = os.path.basename(path)
        return f"{parent}/{filename}"
    except:
        return os.path.basename(path)

def get_similarity_class(score):
    if score >= 0.95:
        return "similarity-high"
    elif score >= 0.88:
        return "similarity-medium"
    return "similarity-low"