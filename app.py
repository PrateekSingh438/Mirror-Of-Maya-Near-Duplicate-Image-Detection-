import streamlit as st
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
import config
from engine import DuplicateDetector
from utils import organize_clusters, get_dir_size, calculate_wasted_space, format_file_size

st.set_page_config(
    page_title="Mirror of Maya", 
    layout=config.LAYOUT, 
    page_icon="🔍",
    initial_sidebar_state="expanded"
)

# Enhanced Ancient Indian Theme CSS (No Religious Symbols)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700&family=Cormorant+Garamond:wght@300;400;600&display=swap');
    
    /* Main Background with Subtle Pattern */
    .main {
        background: linear-gradient(135deg, #0a0e27 0%, #1a1432 25%, #2d1b3d 50%, #1a1432 75%, #0a0e27 100%);
        background-size: 400% 400%;
        animation: gradientShift 15s ease infinite;
        color: #e8d5b7;
        position: relative;
    }
    
    .main::before {
        content: "";
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-image: 
            radial-gradient(circle at 20% 30%, rgba(139, 92, 246, 0.03) 0%, transparent 50%),
            radial-gradient(circle at 80% 70%, rgba(236, 72, 153, 0.03) 0%, transparent 50%),
            radial-gradient(circle at 50% 50%, rgba(251, 191, 36, 0.02) 0%, transparent 50%);
        pointer-events: none;
        z-index: 0;
    }
    
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0a1e 0%, #1a1230 50%, #0f0a1e 100%);
        border-right: 2px solid #c9a86a;
        box-shadow: 4px 0 20px rgba(201, 168, 106, 0.1);
    }
    
    [data-testid="stSidebar"] * {
        color: #e8d5b7 !important;
    }
    
    /* Headers with Elegant Styling */
    .main-header {
        font-family: 'Cinzel', serif;
        font-size: 3.5rem;
        font-weight: 700;
        text-align: center;
        background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 25%, #d97706 50%, #f59e0b 75%, #fbbf24 100%);
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
        animation: shimmer 3s linear infinite;
        letter-spacing: 2px;
        text-shadow: 0 0 30px rgba(251, 191, 36, 0.3);
    }
    
    @keyframes shimmer {
        to { background-position: 200% center; }
    }
    
    .subtitle {
        font-family: 'Cormorant Garamond', serif;
        font-size: 1.4rem;
        text-align: center;
        background: linear-gradient(90deg, #c9a86a 0%, #e8d5b7 50%, #c9a86a 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-style: italic;
        margin-bottom: 2rem;
        opacity: 0.95;
        letter-spacing: 1px;
    }
    
    /* Metric Cards - Elegant Glass Morphism */
    .metric-card {
        background: linear-gradient(135deg, rgba(42, 35, 58, 0.7) 0%, rgba(26, 18, 48, 0.8) 100%);
        backdrop-filter: blur(10px);
        padding: 1.8rem;
        border-radius: 20px;
        border: 1px solid rgba(201, 168, 106, 0.3);
        box-shadow: 
            0 8px 32px rgba(0, 0, 0, 0.3),
            inset 0 1px 1px rgba(255, 255, 255, 0.1);
        position: relative;
        overflow: hidden;
        transition: all 0.3s ease;
    }
    
    .metric-card::before {
        content: "";
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(251, 191, 36, 0.1), transparent);
        transition: left 0.5s;
    }
    
    .metric-card:hover::before {
        left: 100%;
    }
    
    /* Buttons - Premium Styling */
    .stButton>button {
        font-family: 'Cinzel', serif;
        width: 100%;
        border-radius: 12px;
        font-weight: 600;
        background: linear-gradient(135deg, #c9a86a 0%, #a88c5a 100%);
        color: #0a0e27 !important;
        border: 2px solid rgba(251, 191, 36, 0.3);
        box-shadow: 
            0 4px 15px rgba(201, 168, 106, 0.3),
            inset 0 1px 1px rgba(255, 255, 255, 0.2);
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 
            0 6px 25px rgba(251, 191, 36, 0.5),
            inset 0 1px 1px rgba(255, 255, 255, 0.3);
        background: linear-gradient(135deg, #fbbf24 0%, #c9a86a 100%);
    }
    
    /* Primary Button - Accent Style */
    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
        color: #e8d5b7 !important;
        border: 2px solid rgba(139, 92, 246, 0.5);
        box-shadow: 
            0 4px 20px rgba(139, 92, 246, 0.4),
            inset 0 1px 1px rgba(255, 255, 255, 0.2);
    }
    
    .stButton>button[kind="primary"]:hover {
        background: linear-gradient(135deg, #a78bfa 0%, #8b5cf6 100%);
        box-shadow: 0 6px 30px rgba(139, 92, 246, 0.6);
    }
    
    /* Tabs - Modern Architecture */
    .stTabs [data-baseweb="tab-list"] {
        background: linear-gradient(90deg, rgba(15, 10, 30, 0.8) 0%, rgba(26, 18, 48, 0.8) 100%);
        border-bottom: 3px solid rgba(201, 168, 106, 0.5);
        padding: 0.5rem;
        border-radius: 15px 15px 0 0;
        backdrop-filter: blur(10px);
    }
    
    .stTabs [data-baseweb="tab"] {
        font-family: 'Cinzel', serif;
        color: #c9a86a;
        border-radius: 12px 12px 0 0;
        padding: 1rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(201, 168, 106, 0.1);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(180deg, #c9a86a 0%, #a88c5a 100%);
        color: #0a0e27 !important;
        box-shadow: 0 -3px 15px rgba(201, 168, 106, 0.3);
    }
    
    /* Similarity Badges - Elegant Indicators */
    .similarity-badge {
        display: inline-block;
        padding: 0.5rem 1.2rem;
        border-radius: 30px;
        font-weight: 600;
        font-size: 0.95rem;
        font-family: 'Cinzel', serif;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(5px);
        transition: all 0.3s ease;
    }
    
    .similarity-badge:hover {
        transform: scale(1.05);
    }
    
    .similarity-high { 
        background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
        color: #0a0e27;
        border: 2px solid rgba(251, 191, 36, 0.5);
        box-shadow: 0 4px 20px rgba(251, 191, 36, 0.4);
    }
    
    .similarity-medium { 
        background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
        color: #e8d5b7;
        border: 2px solid rgba(139, 92, 246, 0.5);
        box-shadow: 0 4px 20px rgba(139, 92, 246, 0.4);
    }
    
    .similarity-low { 
        background: linear-gradient(135deg, #ec4899 0%, #db2777 100%);
        color: #e8d5b7;
        border: 2px solid rgba(236, 72, 153, 0.5);
        box-shadow: 0 4px 20px rgba(236, 72, 153, 0.4);
    }
    
    /* Container Cards - Premium Glass Effect */
    .duplicate-card {
        border: 1px solid rgba(201, 168, 106, 0.3);
        border-radius: 20px;
        padding: 2rem;
        margin: 1.5rem 0;
        background: linear-gradient(135deg, rgba(42, 35, 58, 0.6) 0%, rgba(26, 18, 48, 0.7) 100%);
        backdrop-filter: blur(10px);
        box-shadow: 
            0 8px 32px rgba(0, 0, 0, 0.3),
            inset 0 1px 1px rgba(255, 255, 255, 0.05);
        position: relative;
    }
    
    /* Expander - Elegant Scroll */
    .streamlit-expanderHeader {
        font-family: 'Cinzel', serif;
        background: linear-gradient(90deg, rgba(42, 35, 58, 0.5) 0%, rgba(26, 18, 48, 0.6) 100%);
        border: 1px solid rgba(201, 168, 106, 0.3);
        border-radius: 12px;
        color: #c9a86a !important;
        backdrop-filter: blur(5px);
        transition: all 0.3s ease;
    }
    
    .streamlit-expanderHeader:hover {
        background: linear-gradient(90deg, rgba(42, 35, 58, 0.7) 0%, rgba(26, 18, 48, 0.8) 100%);
        border-color: rgba(251, 191, 36, 0.5);
    }
    
    /* Input Fields - Modern Manuscripts */
    .stTextInput>div>div>input {
        background: rgba(26, 18, 48, 0.6);
        color: #e8d5b7;
        border: 2px solid rgba(201, 168, 106, 0.3);
        border-radius: 10px;
        font-family: 'Cormorant Garamond', serif;
        backdrop-filter: blur(5px);
        transition: all 0.3s ease;
    }
    
    .stTextInput>div>div>input:focus {
        border-color: #fbbf24;
        box-shadow: 0 0 15px rgba(251, 191, 36, 0.3);
    }
    
    /* Slider - Smooth Gradient Trail */
    .stSlider>div>div>div>div {
        background: linear-gradient(90deg, #8b5cf6 0%, #ec4899 50%, #fbbf24 100%);
        box-shadow: 0 2px 10px rgba(139, 92, 246, 0.3);
    }
    
    /* Info/Warning Boxes */
    .stAlert {
        background: linear-gradient(135deg, rgba(42, 35, 58, 0.6) 0%, rgba(26, 18, 48, 0.7) 100%);
        backdrop-filter: blur(10px);
        border-left: 4px solid #c9a86a;
        color: #e8d5b7;
        font-family: 'Cormorant Garamond', serif;
        border-radius: 10px;
    }
    
    /* Dataframe Styling */
    .dataframe {
        background: rgba(26, 18, 48, 0.6);
        color: #e8d5b7;
        border: 2px solid rgba(201, 168, 106, 0.3);
        border-radius: 15px;
        backdrop-filter: blur(5px);
    }
    
    /* Dividers - Elegant Separators */
    hr {
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent 0%, rgba(201, 168, 106, 0.5) 20%, #c9a86a 50%, rgba(201, 168, 106, 0.5) 80%, transparent 100%);
        margin: 2.5rem 0;
        box-shadow: 0 1px 3px rgba(201, 168, 106, 0.2);
    }
    
    /* Metrics - Elegant Numbers */
    [data-testid="stMetricValue"] {
        font-family: 'Cinzel', serif;
        color: #fbbf24;
        font-size: 2.2rem;
        text-shadow: 0 2px 10px rgba(251, 191, 36, 0.3);
    }
    
    [data-testid="stMetricLabel"] {
        font-family: 'Cormorant Garamond', serif;
        color: #c9a86a;
        font-size: 1.1rem;
        letter-spacing: 0.5px;
    }
    
    /* Decorative Accent */
    .accent-line {
        height: 3px;
        background: linear-gradient(90deg, transparent 0%, #8b5cf6 25%, #ec4899 50%, #fbbf24 75%, transparent 100%);
        margin: 1.5rem 0;
        border-radius: 2px;
        box-shadow: 0 2px 10px rgba(139, 92, 246, 0.3);
    }
    
    /* Image captions */
    .stImage>div>div>p {
        font-family: 'Cormorant Garamond', serif;
        color: #c9a86a;
        font-style: italic;
    }
    
    /* Checkbox */
    .stCheckbox>label {
        font-family: 'Cormorant Garamond', serif;
        color: #c9a86a;
    }
    
    /* Progress Bar - Vibrant Energy */
    .stProgress>div>div>div>div {
        background: linear-gradient(90deg, #8b5cf6 0%, #ec4899 50%, #fbbf24 100%);
        box-shadow: 0 2px 15px rgba(139, 92, 246, 0.5);
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(26, 18, 48, 0.5);
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, #c9a86a 0%, #a88c5a 100%);
        border-radius: 5px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(180deg, #fbbf24 0%, #c9a86a 100%);
    }
</style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---
def get_short_path(path):
    """Returns 'parent_folder/filename' for easier identification"""
    try:
        if not path: return ""
        parent = os.path.basename(os.path.dirname(path))
        filename = os.path.basename(path)
        return f"{parent}/{filename}"
    except:
        return os.path.basename(path)

def get_similarity_class(score):
    """Returns CSS class based on similarity score"""
    if score >= 0.90:
        return "similarity-high"
    elif score >= 0.75:
        return "similarity-medium"
    return "similarity-low"

def save_session_state():
    """Save critical session state to disk"""
    try:
        state_data = {
            'optimal_thresh': st.session_state.optimal_thresh,
            'f1_score': st.session_state.f1_score,
            'calibration_history': st.session_state.calibration_history,
            'deletion_queue': list(st.session_state.deletion_queue),
            'last_scan': datetime.now().isoformat()
        }
        with open('session_state.json', 'w') as f:
            json.dump(state_data, f)
    except Exception as e:
        st.warning(f"Could not save session: {str(e)}")

def load_session_state():
    """Load previous session state if available"""
    try:
        if os.path.exists('session_state.json'):
            with open('session_state.json', 'r') as f:
                state_data = json.load(f)
                st.session_state.optimal_thresh = state_data.get('optimal_thresh', config.DEFAULT_THRESHOLD)
                st.session_state.f1_score = state_data.get('f1_score', 0.0)
                st.session_state.calibration_history = state_data.get('calibration_history', [])
                st.session_state.deletion_queue = set(state_data.get('deletion_queue', []))
                return state_data.get('last_scan')
    except:
        pass
    return None

# Initialize Session State
if 'detector' not in st.session_state: 
    st.session_state.detector = None
if 'duplicates' not in st.session_state: 
    st.session_state.duplicates = []
if 'deletion_queue' not in st.session_state: 
    st.session_state.deletion_queue = set()
if 'f1_score' not in st.session_state: 
    st.session_state.f1_score = 0.0
if 'optimal_thresh' not in st.session_state: 
    st.session_state.optimal_thresh = config.DEFAULT_THRESHOLD
if 'calibration_history' not in st.session_state: 
    st.session_state.calibration_history = []
if 'current_slider_val' not in st.session_state: 
    st.session_state.current_slider_val = config.DEFAULT_THRESHOLD
if 'scan_stats' not in st.session_state:
    st.session_state.scan_stats = {}

# Load previous session
last_scan = load_session_state()

# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown("### ⚙️ Control Panel")
    st.markdown('<div class="accent-line"></div>', unsafe_allow_html=True)
    
    # Dataset Configuration
    with st.expander("📁 Dataset Configuration", expanded=True):
        dataset_path = st.text_input("Dataset Path", value=config.DATASET_PATH)
        
        if os.path.exists(dataset_path):
            dir_size = get_dir_size(dataset_path)
            st.success(f"✓ Path Valid • {dir_size:.1f} MB")
        else:
            st.error("❌ Invalid Path")
    
    # Advanced Settings
    with st.expander("🔧 Advanced Settings", expanded=False):
        st.markdown("*Fine-tune detection parameters*")
        enable_quality = st.checkbox("Quality Metrics", value=config.ENABLE_QUALITY_METRICS)
        enable_dbscan = st.checkbox("DBSCAN Clustering", value=config.USE_DBSCAN_CLUSTERING)
        enable_tta = st.checkbox("Enhanced TTA (Slower)", value=config.ENABLE_ADVANCED_TTA)
        
        batch_size = st.slider("Batch Size", 8, 64, config.BATCH_SIZE, 8)
        st.caption("Higher = faster but more memory")
    
    st.markdown('<div class="accent-line"></div>', unsafe_allow_html=True)
    
    # Scan Buttons
    st.markdown("### 🚀 Detection Engine")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Full Scan", type="primary", use_container_width=True):
            if not os.path.exists(dataset_path):
                st.error("Invalid path!")
            else:
                start_time = datetime.now()
                
                with st.spinner("🔍 Initializing..."):
                    detector = DuplicateDetector()
                
                with st.spinner("📊 Indexing images..."):
                    detector.bulk_index(dataset_path)
                    st.session_state.detector = detector
                
                with st.spinner("⚖️ Calibrating..."):
                    thresh, f1, history = detector.calibrate_threshold(dataset_path)
                    st.session_state.optimal_thresh = thresh
                    st.session_state.f1_score = f1
                    st.session_state.calibration_history = history
                    st.session_state.current_slider_val = thresh
                
                with st.spinner("🔎 Finding duplicates..."):
                    min_thresh = min(config.CALIBRATION_THRESHOLDS)
                    dups = detector.find_duplicates(threshold=min_thresh)
                    st.session_state.duplicates = dups
                
                scan_time = (datetime.now() - start_time).total_seconds()
                st.session_state.scan_stats = {
                    'total_images': detector.index.ntotal,
                    'scan_time': scan_time,
                    'duplicates_found': len(dups),
                    'timestamp': datetime.now().isoformat()
                }
                
                save_session_state()
                st.success(f"✅ Complete! F1: {f1:.4f} @ {thresh:.2f}")
                st.rerun()
    
    with col2:
        if st.button("⚡ Quick Scan", use_container_width=True):
            if st.session_state.detector:
                with st.spinner("🔄 Updating..."):
                    st.session_state.detector.bulk_index(dataset_path)
                    dups = st.session_state.detector.find_duplicates()
                    st.session_state.duplicates = dups
                st.success("✅ Updated!")
                st.rerun()
            else:
                st.warning("Run Full Scan first")
    
    # Session Info
    if st.session_state.detector:
        st.markdown('<div class="accent-line"></div>', unsafe_allow_html=True)
        st.markdown("### 📊 Session Statistics")
        
        stats = st.session_state.scan_stats
        if stats:
            st.metric("🖼️ Total Images", f"{stats.get('total_images', 0):,}")
            st.metric("⏱️ Scan Time", f"{stats.get('scan_time', 0):.1f}s")
            if last_scan:
                st.caption(f"*Last scan: {last_scan[:10]}*")
        
        st.metric("🎯 Optimal Threshold", f"{st.session_state.optimal_thresh:.2f}")
        st.metric("📈 F1 Score", f"{st.session_state.f1_score:.4f}")
        
        st.markdown('<div class="accent-line"></div>', unsafe_allow_html=True)
        
        # Export options
        if st.button("💾 Export Results", use_container_width=True):
            if st.session_state.duplicates:
                df = pd.DataFrame([
                    {
                        'File 1': d['file1'],
                        'File 2': d['file2'],
                        'Similarity': d['score'],
                        'Method': d['method']
                    }
                    for d in st.session_state.duplicates
                ])
                csv = df.to_csv(index=False)
                st.download_button(
                    "⬇️ Download CSV",
                    csv,
                    f"duplicates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "text/csv"
                )

# ==================== MAIN CONTENT ====================
st.markdown('<h1 class="main-header">MIRROR OF MAYA</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Piercing the Veil of Digital Illusion</p>', unsafe_allow_html=True)

# Philosophy Quote
st.markdown("""
<div style='text-align: center; padding: 2rem; 
     background: linear-gradient(135deg, rgba(42, 35, 58, 0.6) 0%, rgba(26, 18, 48, 0.7) 100%);
     backdrop-filter: blur(10px);
     border-radius: 20px; border: 1px solid rgba(201, 168, 106, 0.3); 
     margin-bottom: 2rem; font-family: "Cormorant Garamond", serif;
     box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);'>
    <em style='color: #c9a86a; font-size: 1.15rem; line-height: 1.8;'>
    "Maya represents the veil of illusion where one truth takes a thousand forms.<br>
    Just as reality manifests in countless appearances, digital images spawn endless duplicates.<br>
    This system of discernment cuts through illusion to reveal the original essence."
    </em>
</div>
""", unsafe_allow_html=True)

# Status Bar
if st.session_state.detector:
    active_thresh = st.session_state.get('current_slider_val', st.session_state.optimal_thresh)
    visible_dups = [d for d in st.session_state.duplicates if d['score'] >= active_thresh]
    waste = calculate_wasted_space(visible_dups)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🔍 Duplicates Found", f"{len(visible_dups):,}")
    col2.metric("💾 Wasted Space", format_file_size(waste * 1024 * 1024))
    col3.metric("🎯 F1 Score", f"{st.session_state.f1_score:.4f}")
    col4.metric("📊 Threshold", f"{active_thresh:.2f}")

st.markdown('<div class="accent-line"></div>', unsafe_allow_html=True)

tabs = st.tabs(["📊 Dashboard", "🗂️ Duplicate Manager", "🔎 Image Search", "📈 Analytics"])

# ==================== DASHBOARD TAB ====================
with tabs[0]:
    if not st.session_state.duplicates:
        st.markdown("""
        <div style='text-align: center; padding: 3rem; 
             background: linear-gradient(135deg, rgba(42, 35, 58, 0.6) 0%, rgba(26, 18, 48, 0.7) 100%);
             backdrop-filter: blur(10px);
             border-radius: 20px; border: 1px solid rgba(201, 168, 106, 0.3);
             box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);'>
            <h3 style='color: #fbbf24; font-family: "Cinzel", serif;'>🔍 Ready to Begin</h3>
            <p style='color: #e8d5b7; font-family: "Cormorant Garamond", serif; font-size: 1.1rem;'>
            Click "Full Scan" in the sidebar to start detecting duplicates
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Show helpful guide
        with st.expander("📖 Quick Start Guide", expanded=True):
            st.markdown("""
            <div style='font-family: "Cormorant Garamond", serif; color: #e8d5b7;'>
            
            ### 🚀 Getting Started:
            
            **1. Configure Dataset Path** 📁  
            *Enter the location of your image folder in the Control Panel*
            
            **2. Run Full Scan** 🔄  
            *The system will index images and auto-calibrate optimal threshold*
            
            **3. Review Results** 👁️  
            *Navigate to Duplicate Manager to see grouped duplicates*
            
            **4. Select & Remove** 🗑️  
            *Mark duplicates for deletion and purify your dataset*
            
            **5. Export Data** 📜  
            *Download results as CSV for documentation*
            
            ---
            
            ### ✨ Features:
            
            - **Auto-calibration** finds optimal detection threshold
            - **Slider control** filters results by confidence level
            - **Quality metrics** identify the best version of duplicates
            - **F1 Score** measures detection accuracy
            
            </div>
            """, unsafe_allow_html=True)
    else:
        active_thresh = st.session_state.get('current_slider_val', st.session_state.optimal_thresh)
        visible_dups = [d for d in st.session_state.duplicates if d['score'] >= active_thresh]
        
        # Calibration Analysis
        if st.session_state.calibration_history:
            st.markdown("### 📈 Threshold Calibration Analysis")
            st.markdown("*System tested multiple thresholds to find optimal balance*")
            
            col_chart, col_table = st.columns([2, 1])
            
            df_cal = pd.DataFrame(st.session_state.calibration_history)
            
            with col_chart:
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=df_cal['threshold'], y=df_cal['f1'],
                    mode='lines+markers', name='F1 Score',
                    line=dict(color='#fbbf24', width=3),
                    marker=dict(size=10, symbol='diamond')
                ))
                
                fig.add_trace(go.Scatter(
                    x=df_cal['threshold'], y=df_cal['precision'],
                    mode='lines+markers', name='Precision',
                    line=dict(color='#8b5cf6', width=2),
                    marker=dict(size=8)
                ))
                
                fig.add_trace(go.Scatter(
                    x=df_cal['threshold'], y=df_cal['recall'],
                    mode='lines+markers', name='Recall',
                    line=dict(color='#ec4899', width=2),
                    marker=dict(size=8)
                ))
                
                # Mark optimal point
                optimal_row = df_cal[df_cal['threshold'] == st.session_state.optimal_thresh].iloc[0]
                fig.add_trace(go.Scatter(
                    x=[optimal_row['threshold']],
                    y=[optimal_row['f1']],
                    mode='markers',
                    name='Optimal Point',
                    marker=dict(size=20, color='#10b981', symbol='star')
                ))
                
                fig.update_layout(
                    title="Performance vs Threshold",
                    xaxis_title="Similarity Threshold",
                    yaxis_title="Score (0-1)",
                    hovermode='x unified',
                    height=400,
                    plot_bgcolor='rgba(26, 18, 48, 0.4)',
                    paper_bgcolor='rgba(0, 0, 0, 0)',
                    font=dict(color='#e8d5b7', family='Cormorant Garamond')
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            with col_table:
                st.dataframe(
                    df_cal[["threshold", "f1", "precision", "recall", "count"]]
                    .style.highlight_max(axis=0, subset=["f1"])
                    .format({
                        'f1': '{:.4f}',
                        'precision': '{:.4f}',
                        'recall': '{:.4f}',
                        'threshold': '{:.2f}'
                    }),
                    use_container_width=True,
                    height=400
                )
        
        st.markdown("---")
        
        # Distribution Analysis
        st.markdown("### 📊 Similarity Score Distribution")
        
        scores = [d['score'] for d in visible_dups]
        if scores:
            fig = px.histogram(
                scores,
                nbins=30,
                title="Distribution of Similarity Scores",
                labels={'value': 'Similarity Score', 'count': 'Number of Pairs'},
                color_discrete_sequence=['#c9a86a']
            )
            fig.add_vline(
                x=active_thresh,
                line_dash="dash",
                line_color="#fbbf24",
                annotation_text="Active Threshold",
                annotation=dict(font=dict(color='#e8d5b7'))
            )
            fig.update_layout(
                plot_bgcolor='rgba(26, 18, 48, 0.4)',
                paper_bgcolor='rgba(0, 0, 0, 0)',
                font=dict(color='#e8d5b7', family='Cormorant Garamond')
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Method breakdown
        col1, col2 = st.columns(2)
        
        with col1:
            method_counts = pd.Series([d['method'] for d in visible_dups]).value_counts()
            fig = px.pie(
                values=method_counts.values,
                names=method_counts.index,
                title="Detection Methods Used",
                color_discrete_sequence=['#fbbf24', '#8b5cf6', '#ec4899']
            )
            fig.update_layout(
                plot_bgcolor='rgba(26, 18, 48, 0.4)',
                paper_bgcolor='rgba(0, 0, 0, 0)',
                font=dict(color='#e8d5b7', family='Cormorant Garamond')
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            ranges = pd.cut(scores, bins=[0, 0.7, 0.85, 0.95, 1.0], labels=['Weak', 'Moderate', 'Strong', 'Very Strong'])
            range_counts = ranges.value_counts()
            fig = px.bar(
                x=range_counts.index,
                y=range_counts.values,
                title="Confidence Level Distribution",
                labels={'x': 'Strength', 'y': 'Count'},
                color_discrete_sequence=['#c9a86a']
            )
            fig.update_layout(
                plot_bgcolor='rgba(26, 18, 48, 0.4)',
                paper_bgcolor='rgba(0, 0, 0, 0)',
                font=dict(color='#e8d5b7', family='Cormorant Garamond')
            )
            st.plotly_chart(fig, use_container_width=True)

# ==================== DUPLICATE MANAGER TAB ====================
with tabs[1]:
    if st.session_state.duplicates:
        st.markdown("### 🎚️ Similarity Threshold Control")
        
        col_slider, col_info = st.columns([3, 1])
        
        with col_slider:
            new_thresh = st.slider(
                "Minimum Similarity Score",
                min_value=0.60,
                max_value=0.99,
                value=st.session_state.current_slider_val,
                step=0.01,
                help="Adjust threshold to filter matches by confidence"
            )
            if new_thresh != st.session_state.current_slider_val:
                st.session_state.current_slider_val = new_thresh
                st.rerun()
        
        with col_info:
            st.metric("Showing", f"≥ {st.session_state.current_slider_val:.0%}")
        
        active_dups = [d for d in st.session_state.duplicates if d['score'] >= st.session_state.current_slider_val]
        clusters = organize_clusters(active_dups)
        
        st.info(f"📦 Found **{len(clusters)}** groups (**{len(active_dups)}** total pairs)")
        
        # Bulk actions
        col1, col2, col3, col4 = st.columns(4)
        
        if col1.button("✅ Select All Visible", use_container_width=True):
            for c in clusters:
                for d in c['duplicates']:
                    st.session_state.deletion_queue.add(d['path'])
            st.rerun()
        
        if col2.button("🔄 Clear Selection", use_container_width=True):
            st.session_state.deletion_queue.clear()
            st.rerun()
        
        if col3.button("💾 Save Progress", use_container_width=True):
            save_session_state()
            st.success("Progress saved!")
        
        if st.session_state.deletion_queue:
            if col4.button(
                f"🗑️ DELETE {len(st.session_state.deletion_queue)} FILES",
                type="primary",
                use_container_width=True
            ):
                deleted = 0
                failed = []
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                total = len(st.session_state.deletion_queue)
                
                for i, f in enumerate(list(st.session_state.deletion_queue)):
                    status_text.text(f"Deleting {i+1}/{total}...")
                    try:
                        os.remove(f)
                        st.session_state.deletion_queue.discard(f)
                        deleted += 1
                    except Exception as e:
                        failed.append((f, str(e)))
                    progress_bar.progress((i + 1) / total)
                
                st.session_state.duplicates = [
                    d for d in st.session_state.duplicates 
                    if os.path.exists(d['file1']) and os.path.exists(d['file2'])
                ]
                
                if failed:
                    st.warning(f"⚠️ Deleted {deleted} files. {len(failed)} failed.")
                else:
                    st.success(f"✅ Successfully deleted {deleted} files!")
                
                save_session_state()
                st.rerun()
        
        st.markdown("---")
        
        # Pagination
        if 'page' not in st.session_state:
            st.session_state.page = 0
        
        total_pages = max(1, (len(clusters) - 1) // config.CLUSTERS_PER_PAGE + 1)
        start = st.session_state.page * config.CLUSTERS_PER_PAGE
        end = min(start + config.CLUSTERS_PER_PAGE, len(clusters))
        
        # Display clusters
        for i, cluster in enumerate(clusters[start:end]):
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, rgba(42, 35, 58, 0.6) 0%, rgba(26, 18, 48, 0.7) 100%); 
                 backdrop-filter: blur(10px);
                 padding: 1.5rem; border-radius: 20px; 
                 border: 1px solid rgba(201, 168, 106, 0.3); 
                 margin: 1rem 0;
                 box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);'>
                <h4 style='color: #fbbf24; font-family: "Cinzel", serif;'>
                    📁 Group {start + i + 1}
                </h4>
            </div>
            """, unsafe_allow_html=True)
            
            col_orig, col_dups = st.columns([1, 3])
            
            with col_orig:
                st.markdown("**Original**")
                try:
                    st.image(cluster['original'], use_container_width=True)
                    st.caption(f"📂 {get_short_path(cluster['original'])}")
                except:
                    st.error("Could not load original")
            
            with col_dups:
                st.markdown("**Duplicates**")
                if cluster['duplicates']:
                    dup_cols = st.columns(min(len(cluster['duplicates']), 3))
                    
                    for idx, dup in enumerate(cluster['duplicates']):
                        c = dup_cols[idx % 3]
                        
                        try:
                            c.image(dup['path'], use_container_width=True)
                            
                            score_pct = dup['score'] * 100
                            badge_class = get_similarity_class(dup['score'])
                            
                            c.markdown(
                                f'<span class="similarity-badge {badge_class}">{score_pct:.1f}%</span>',
                                unsafe_allow_html=True
                            )
                            c.caption(f"📂 {get_short_path(dup['path'])}")
                            
                            is_selected = c.checkbox(
                                "Delete",
                                key=f"del_{start+i}_{idx}",
                                value=dup['path'] in st.session_state.deletion_queue
                            )
                            
                            if is_selected:
                                st.session_state.deletion_queue.add(dup['path'])
                            else:
                                st.session_state.deletion_queue.discard(dup['path'])
                        except Exception as e:
                            c.error(f"Error: {str(e)}")
            
            st.markdown("---")
        
        # Pagination controls
        col_prev, col_info, col_next = st.columns([1, 2, 1])
        
        with col_prev:
            if st.session_state.page > 0:
                if st.button("⬅️ Previous", use_container_width=True):
                    st.session_state.page -= 1
                    st.rerun()
        
        with col_info:
            st.markdown(f"<div style='text-align: center; font-family: \"Cinzel\", serif; color: #fbbf24;'>Page {st.session_state.page + 1} of {total_pages}</div>", unsafe_allow_html=True)
        
        with col_next:
            if end < len(clusters):
                if st.button("Next ➡️", use_container_width=True):
                    st.session_state.page += 1
                    st.rerun()
    else:
        st.markdown("""
        <div style='text-align: center; padding: 3rem; 
             background: linear-gradient(135deg, rgba(42, 35, 58, 0.6) 0%, rgba(26, 18, 48, 0.7) 100%);
             backdrop-filter: blur(10px);
             border-radius: 20px; border: 1px solid rgba(201, 168, 106, 0.3);
             box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);'>
            <h3 style='color: #fbbf24; font-family: "Cinzel", serif;'>No Duplicates Yet</h3>
            <p style='color: #e8d5b7; font-family: "Cormorant Garamond", serif;'>
            Run a Full Scan to discover duplicate images
            </p>
        </div>
        """, unsafe_allow_html=True)

# ==================== IMAGE SEARCH TAB ====================
with tabs[2]:
    st.markdown("### 🔍 Search for Similar Images")
    st.markdown("*Upload an image to find similar matches in your dataset*")
    
    col_upload, col_settings = st.columns([2, 1])
    
    with col_upload:
        uploaded = st.file_uploader(
            "Choose an image file",
            type=['png', 'jpg', 'jpeg', 'bmp', 'webp']
        )
    
    with col_settings:
        query_threshold = st.slider(
            "Match Threshold",
            0.60, 0.99,
            st.session_state.current_slider_val,
            0.01,
            key="query_thresh"
        )
        max_results = st.number_input("Max Results", 1, 50, 10)
    
    if uploaded and st.session_state.detector:
        with open(config.TEMP_QUERY_FILE, "wb") as f:
            f.write(uploaded.getbuffer())
        
        st.markdown("#### 🖼️ Query Image")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(config.TEMP_QUERY_FILE, use_container_width=True)
        
        with st.spinner("🔎 Searching..."):
            results = st.session_state.detector.find_matches_for_file(
                config.TEMP_QUERY_FILE,
                threshold=query_threshold
            )
        
        if results:
            st.success(f"✨ Found {len(results)} similar images!")
            
            results = results[:max_results]
            
            st.markdown("#### 📸 Search Results")
            for i in range(0, len(results), 3):
                cols = st.columns(3)
                for j, col in enumerate(cols):
                    if i + j < len(results):
                        res = results[i + j]
                        with col:
                            try:
                                st.image(res['path'], use_container_width=True)
                                score_pct = res['score'] * 100
                                badge_class = get_similarity_class(res['score'])
                                st.markdown(
                                    f'<span class="similarity-badge {badge_class}">{score_pct:.1f}% Match</span>',
                                    unsafe_allow_html=True
                                )
                                st.caption(f"📂 {get_short_path(res['path'])}")
                            except:
                                st.error("Could not load image")
        else:
            st.warning(f"No matches found at {query_threshold:.0%} threshold. Try lowering the threshold.")
    
    elif not st.session_state.detector:
        st.info("🔍 Run a Full Scan first to enable image search")

# ==================== ANALYTICS TAB ====================
with tabs[3]:
    st.markdown("### 📈 Advanced Analytics")
    
    if st.session_state.duplicates:
        active_thresh = st.session_state.current_slider_val
        visible_dups = [d for d in st.session_state.duplicates if d['score'] >= active_thresh]
        
        # Summary statistics
        col1, col2, col3 = st.columns(3)
        
        scores = [d['score'] for d in visible_dups]
        
        with col1:
            st.metric("📊 Mean Similarity", f"{sum(scores)/len(scores):.3f}" if scores else "N/A")
            st.metric("📈 Median Similarity", f"{sorted(scores)[len(scores)//2]:.3f}" if scores else "N/A")
        
        with col2:
            st.metric("📉 Min Similarity", f"{min(scores):.3f}" if scores else "N/A")
            st.metric("📊 Max Similarity", f"{max(scores):.3f}" if scores else "N/A")
        
        with col3:
            clusters = organize_clusters(visible_dups)
            avg_cluster_size = sum(len(c['duplicates']) for c in clusters) / len(clusters) if clusters else 0
            st.metric("📦 Avg Group Size", f"{avg_cluster_size:.1f}")
            st.metric("🗂️ Total Groups", len(clusters))
        
        st.markdown("---")
        
        # Detailed dataframe
        st.markdown("### 📋 Complete Duplicate List")
        
        df_details = pd.DataFrame([
            {
                'File 1': get_short_path(d['file1']),
                'File 2': get_short_path(d['file2']),
                'Similarity': f"{d['score']:.3f}",
                'Method': d['method'],
                'Marked': '✓' if d['file2'] in st.session_state.deletion_queue else ''
            }
            for d in visible_dups
        ])
        
        st.dataframe(df_details, use_container_width=True, height=400)
        
    else:
        st.markdown("""
        <div style='text-align: center; padding: 3rem; 
             background: linear-gradient(135deg, rgba(42, 35, 58, 0.6) 0%, rgba(26, 18, 48, 0.7) 100%);
             backdrop-filter: blur(10px);
             border-radius: 20px; border: 1px solid rgba(201, 168, 106, 0.3);
             box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);'>
            <h3 style='color: #fbbf24; font-family: "Cinzel", serif;'>No Data Available</h3>
            <p style='color: #e8d5b7; font-family: "Cormorant Garamond", serif;'>
            Run a Full Scan to view analytics
            </p>
        </div>
        """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown(f"""
<div style='text-align: center; font-family: "Cormorant Garamond", serif; color: #c9a86a; padding: 2rem;'>
    <div class='accent-line' style='margin-bottom: 1rem;'></div>
    <p style='font-size: 1.2rem; font-family: "Cinzel", serif;'>Mirror of Maya</p>
    <p><em>Where illusion meets discernment</em></p>
    <p style='font-size: 0.9rem; opacity: 0.7;'>{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
</div>
""", unsafe_allow_html=True)