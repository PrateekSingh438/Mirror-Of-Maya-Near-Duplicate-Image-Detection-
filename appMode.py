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

# Ultra-Modern UI Theme
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');
    
    /* Main Background - Dark Mode Pro */
    .main {
        background: #0f0f23;
        background-image: 
            radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.15) 0px, transparent 50%),
            radial-gradient(at 100% 0%, rgba(168, 85, 247, 0.15) 0px, transparent 50%),
            radial-gradient(at 100% 100%, rgba(236, 72, 153, 0.15) 0px, transparent 50%),
            radial-gradient(at 0% 100%, rgba(59, 130, 246, 0.15) 0px, transparent 50%);
        color: #e2e8f0;
        position: relative;
    }
    
    /* Animated Grid Background */
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
    
    /* Sidebar - Premium Dark */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
        border-right: 1px solid rgba(99, 102, 241, 0.2);
        box-shadow: 4px 0 24px rgba(0, 0, 0, 0.5);
    }
    
    [data-testid="stSidebar"] * {
        color: #e2e8f0 !important;
    }
    
    /* Main Header - Ultra Modern */
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
        position: relative;
    }
    
    .main-header::after {
        content: "";
        position: absolute;
        bottom: -10px;
        left: 50%;
        transform: translateX(-50%);
        width: 100px;
        height: 4px;
        background: linear-gradient(90deg, #6366f1, #a855f7, #ec4899);
        border-radius: 2px;
        box-shadow: 0 0 20px rgba(99, 102, 241, 0.5);
    }
    
    .subtitle {
        font-family: 'Inter', sans-serif;
        font-size: 1.1rem;
        text-align: center;
        color: #94a3b8;
        font-weight: 400;
        margin-bottom: 3rem;
        letter-spacing: 0.5px;
    }
    
    /* Metric Cards - Neumorphism */
    [data-testid="stMetricValue"] {
        font-family: 'Space Grotesk', sans-serif;
        color: #f8fafc;
        font-size: 2.5rem;
        font-weight: 700;
    }
    
    [data-testid="stMetricLabel"] {
        font-family: 'Inter', sans-serif;
        color: #94a3b8;
        font-size: 0.875rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, rgba(30, 30, 46, 0.8) 0%, rgba(24, 24, 37, 0.9) 100%);
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 
            0 4px 24px rgba(0, 0, 0, 0.3),
            inset 0 1px 0 rgba(255, 255, 255, 0.05);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    div[data-testid="stMetric"]:hover {
        transform: translateY(-4px);
        box-shadow: 
            0 12px 40px rgba(99, 102, 241, 0.2),
            inset 0 1px 0 rgba(255, 255, 255, 0.1);
        border-color: rgba(99, 102, 241, 0.4);
    }
    
    /* Buttons - Modern Gradient */
    .stButton>button {
        font-family: 'Inter', sans-serif;
        width: 100%;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.875rem;
        padding: 0.75rem 1.5rem;
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(168, 85, 247, 0.1) 100%);
        color: #e2e8f0 !important;
        border: 1px solid rgba(99, 102, 241, 0.3);
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(99, 102, 241, 0.3);
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.2) 0%, rgba(168, 85, 247, 0.2) 100%);
        border-color: rgba(99, 102, 241, 0.5);
    }
    
    .stButton>button:active {
        transform: translateY(0);
    }
    
    /* Primary Button */
    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        border: none;
        box-shadow: 
            0 4px 20px rgba(99, 102, 241, 0.4),
            0 0 40px rgba(99, 102, 241, 0.1);
    }
    
    .stButton>button[kind="primary"]:hover {
        background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%);
        box-shadow: 
            0 8px 32px rgba(99, 102, 241, 0.5),
            0 0 60px rgba(99, 102, 241, 0.2);
    }
    
    /* Tabs - Sleek Modern */
    .stTabs [data-baseweb="tab-list"] {
        background: transparent;
        border-bottom: 2px solid rgba(99, 102, 241, 0.2);
        gap: 1rem;
        padding: 0;
    }
    
    .stTabs [data-baseweb="tab"] {
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 0.875rem;
        color: #64748b;
        border: none;
        padding: 1rem 1.5rem;
        background: transparent;
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        color: #94a3b8;
    }
    
    .stTabs [aria-selected="true"] {
        color: #6366f1 !important;
        background: transparent;
        border-bottom: 3px solid #6366f1;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.2);
    }
    
    /* Similarity Badges - Modern Pills */
    .similarity-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 1rem;
        border-radius: 50px;
        font-weight: 600;
        font-size: 0.875rem;
        font-family: 'Inter', sans-serif;
        transition: all 0.3s ease;
        backdrop-filter: blur(10px);
    }
    
    .similarity-badge::before {
        content: "●";
        font-size: 0.75rem;
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
    
    /* Container Cards - Glass Effect */
    .info-card {
        background: linear-gradient(135deg, rgba(30, 30, 46, 0.6) 0%, rgba(24, 24, 37, 0.7) 100%);
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 20px;
        padding: 2rem;
        margin: 1.5rem 0;
        backdrop-filter: blur(20px);
        box-shadow: 
            0 8px 32px rgba(0, 0, 0, 0.3),
            inset 0 1px 0 rgba(255, 255, 255, 0.05);
    }
    
    /* Expander - Clean Design */
    .streamlit-expanderHeader {
        font-family: 'Inter', sans-serif;
        background: rgba(30, 30, 46, 0.4);
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 12px;
        color: #e2e8f0 !important;
        font-weight: 600;
        padding: 1rem 1.5rem;
        transition: all 0.3s ease;
    }
    
    .streamlit-expanderHeader:hover {
        background: rgba(30, 30, 46, 0.6);
        border-color: rgba(99, 102, 241, 0.4);
    }
    
    /* Input Fields */
    .stTextInput>div>div>input {
        background: rgba(30, 30, 46, 0.5);
        color: #e2e8f0;
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 12px;
        font-family: 'Inter', sans-serif;
        padding: 0.75rem 1rem;
        transition: all 0.3s ease;
    }
    
    .stTextInput>div>div>input:focus {
        border-color: #6366f1;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
        background: rgba(30, 30, 46, 0.7);
    }
    
    /* Slider - Modern Track */
    .stSlider>div>div>div>div {
        background: linear-gradient(90deg, #6366f1 0%, #8b5cf6 50%, #ec4899 100%);
        height: 6px;
        border-radius: 3px;
    }
    
    .stSlider>div>div>div>div>div {
        background: white;
        border: 2px solid #6366f1;
        box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
    }
    
    /* Alert Boxes */
    .stAlert {
        background: linear-gradient(135deg, rgba(30, 30, 46, 0.6) 0%, rgba(24, 24, 37, 0.7) 100%);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(99, 102, 241, 0.3);
        border-left: 4px solid #6366f1;
        border-radius: 12px;
        color: #e2e8f0;
        font-family: 'Inter', sans-serif;
    }
    
    /* Dataframe */
    .dataframe {
        background: rgba(30, 30, 46, 0.5);
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 12px;
        font-family: 'Inter', sans-serif;
    }
    
    /* Dividers */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent 0%, rgba(99, 102, 241, 0.3) 50%, transparent 100%);
        margin: 2rem 0;
    }
    
    /* Progress Bar */
    .stProgress>div>div>div>div {
        background: linear-gradient(90deg, #6366f1 0%, #8b5cf6 50%, #ec4899 100%);
        border-radius: 10px;
    }
    
    /* Image Captions */
    .stImage>div>div>p {
        font-family: 'Inter', sans-serif;
        color: #94a3b8;
        font-size: 0.875rem;
    }
    
    /* Checkbox */
    .stCheckbox>label {
        font-family: 'Inter', sans-serif;
        color: #94a3b8;
        font-weight: 500;
    }
    
    /* File Uploader */
    .stFileUploader>div {
        background: rgba(30, 30, 46, 0.5);
        border: 2px dashed rgba(99, 102, 241, 0.3);
        border-radius: 12px;
        transition: all 0.3s ease;
    }
    
    .stFileUploader>div:hover {
        border-color: rgba(99, 102, 241, 0.5);
        background: rgba(30, 30, 46, 0.7);
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(30, 30, 46, 0.5);
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, #6366f1 0%, #8b5cf6 100%);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(180deg, #8b5cf6 0%, #a855f7 100%);
    }
    
    /* Number Input */
    .stNumberInput>div>div>input {
        background: rgba(30, 30, 46, 0.5);
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 12px;
        color: #e2e8f0;
        font-family: 'Inter', sans-serif;
    }
    
    /* Select Box */
    .stSelectbox>div>div {
        background: rgba(30, 30, 46, 0.5);
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 12px;
    }
    
    /* Tooltips */
    [data-baseweb="tooltip"] {
        font-family: 'Inter', sans-serif;
        background: rgba(30, 30, 46, 0.95);
        border: 1px solid rgba(99, 102, 241, 0.3);
    }
    
    /* Loading Spinner */
    .stSpinner>div {
        border-color: #6366f1 transparent transparent transparent;
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
    st.markdown("### ⚙️ CONTROL CENTER")
    st.markdown("---")
    
    # Dataset Configuration
    with st.expander("📁 Dataset Settings", expanded=True):
        dataset_path = st.text_input("Dataset Path", value=config.DATASET_PATH)
        
        if os.path.exists(dataset_path):
            dir_size = get_dir_size(dataset_path)
            st.success(f"✓ {dir_size:.1f} MB indexed")
        else:
            st.error("❌ Path not found")
    
    # Advanced Settings
    with st.expander("🔧 Advanced", expanded=False):
        enable_quality = st.checkbox("Quality Metrics", value=config.ENABLE_QUALITY_METRICS)
        enable_dbscan = st.checkbox("DBSCAN Clustering", value=config.USE_DBSCAN_CLUSTERING)
        enable_tta = st.checkbox("Enhanced TTA", value=config.ENABLE_ADVANCED_TTA)
        batch_size = st.slider("Batch Size", 8, 64, config.BATCH_SIZE, 8)
    
    st.markdown("---")
    
    # Scan Buttons
    st.markdown("### 🚀 ACTIONS")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Full Scan", type="primary", use_container_width=True):
            if not os.path.exists(dataset_path):
                st.error("Invalid path!")
            else:
                start_time = datetime.now()
                
                with st.spinner("Initializing..."):
                    detector = DuplicateDetector()
                
                with st.spinner("Indexing..."):
                    detector.bulk_index(dataset_path)
                    st.session_state.detector = detector
                
                with st.spinner("Calibrating..."):
                    thresh, f1, history = detector.calibrate_threshold(dataset_path)
                    st.session_state.optimal_thresh = thresh
                    st.session_state.f1_score = f1
                    st.session_state.calibration_history = history
                    st.session_state.current_slider_val = thresh
                
                with st.spinner("Finding duplicates..."):
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
                st.success(f"✓ Complete! F1: {f1:.4f}")
                st.rerun()
    
    with col2:
        if st.button("⚡ Quick", use_container_width=True):
            if st.session_state.detector:
                with st.spinner("Updating..."):
                    st.session_state.detector.bulk_index(dataset_path)
                    dups = st.session_state.detector.find_duplicates()
                    st.session_state.duplicates = dups
                st.success("✓ Updated!")
                st.rerun()
            else:
                st.warning("Run Full Scan first")
    
    # Session Info
    if st.session_state.detector:
        st.markdown("---")
        st.markdown("### 📊 STATS")
        
        stats = st.session_state.scan_stats
        if stats:
            st.metric("Images", f"{stats.get('total_images', 0):,}")
            st.metric("Scan Time", f"{stats.get('scan_time', 0):.1f}s")
            st.metric("Threshold", f"{st.session_state.optimal_thresh:.2f}")
            st.metric("F1 Score", f"{st.session_state.f1_score:.4f}")
        
        st.markdown("---")
        
        # Export
        if st.button("💾 Export CSV", use_container_width=True):
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
                    "⬇️ Download",
                    csv,
                    f"duplicates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "text/csv",
                    use_container_width=True
                )

# ==================== MAIN CONTENT ====================
st.markdown('<h1 class="main-header">MIRROR OF MAYA</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Near-Duplicate Image Detection System</p>', unsafe_allow_html=True)

# Status Bar
if st.session_state.detector:
    active_thresh = st.session_state.get('current_slider_val', st.session_state.optimal_thresh)
    visible_dups = [d for d in st.session_state.duplicates if d['score'] >= active_thresh]
    waste = calculate_wasted_space(visible_dups)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("DUPLICATES", f"{len(visible_dups):,}")
    col2.metric("WASTED SPACE", format_file_size(waste * 1024 * 1024))
    col3.metric("F1 SCORE", f"{st.session_state.f1_score:.4f}")
    col4.metric("THRESHOLD", f"{active_thresh:.2f}")

st.markdown("---")

tabs = st.tabs(["📊 Dashboard", "🗂️ Manager", "🔎 Search", "📈 Analytics"])

# ==================== DASHBOARD TAB ====================
with tabs[0]:
    if not st.session_state.duplicates:
        st.markdown("""
        <div class='info-card' style='text-align: center;'>
            <h3 style='color: #6366f1; font-family: "Space Grotesk", sans-serif; margin-bottom: 1rem;'>
                Ready to Scan
            </h3>
            <p style='color: #94a3b8; font-family: "Inter", sans-serif; font-size: 1rem;'>
                Click "Full Scan" in the sidebar to begin detection
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("📖 Quick Guide", expanded=True):
            st.markdown("""
            #### Getting Started
            
            1. **Configure Path** - Set your dataset location
            2. **Run Scan** - System auto-calibrates and indexes
            3. **Review** - Check duplicate groups in Manager tab
            4. **Clean** - Select and delete redundant files
            5. **Export** - Download results as CSV
            
            #### Features
            - Auto-calibration for optimal accuracy
            - Real-time similarity filtering
            - Quality-based duplicate ranking
            - Batch operations support
            """)
    else:
        active_thresh = st.session_state.get('current_slider_val', st.session_state.optimal_thresh)
        visible_dups = [d for d in st.session_state.duplicates if d['score'] >= active_thresh]
        
        # Calibration Analysis
        if st.session_state.calibration_history:
            st.markdown("### Calibration Results")
            
            col_chart, col_table = st.columns([2, 1])
            
            df_cal = pd.DataFrame(st.session_state.calibration_history)
            
            with col_chart:
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=df_cal['threshold'], y=df_cal['f1'],
                    mode='lines+markers', name='F1 Score',
                    line=dict(color='#6366f1', width=3),
                    marker=dict(size=8)
                ))
                
                fig.add_trace(go.Scatter(
                    x=df_cal['threshold'], y=df_cal['precision'],
                    mode='lines+markers', name='Precision',
                    line=dict(color='#8b5cf6', width=2),
                    marker=dict(size=6)
                ))
                
                fig.add_trace(go.Scatter(
                    x=df_cal['threshold'], y=df_cal['recall'],
                    mode='lines+markers', name='Recall',
                    line=dict(color='#ec4899', width=2),
                    marker=dict(size=6)
                ))
                
                optimal_row = df_cal[df_cal['threshold'] == st.session_state.optimal_thresh].iloc[0]
                fig.add_trace(go.Scatter(
                    x=[optimal_row['threshold']],
                    y=[optimal_row['f1']],
                    mode='markers',
                    name='Optimal',
                    marker=dict(size=16, color='#10b981', symbol='star')
                ))
                
                fig.update_layout(
                    xaxis_title="Threshold",
                    yaxis_title="Score",
                    hovermode='x unified',
                    height=350,
                    plot_bgcolor='rgba(15, 15, 35, 0.5)',
                    paper_bgcolor='rgba(0, 0, 0, 0)',
                    font=dict(color='#e2e8f0', family='Inter', size=11),
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            with col_table:
                st.dataframe(
                    df_cal[["threshold", "f1", "precision", "recall"]]
                    .style.highlight_max(axis=0, subset=["f1"])
                    .format({
                        'f1': '{:.3f}',
                        'precision': '{:.3f}',
                        'recall': '{:.3f}',
                        'threshold': '{:.2f}'
                    }),
                    use_container_width=True,
                    height=350
                )
        
        st.markdown("---")
        
        # Distribution Analysis
        col1, col2 = st.columns(2)
        
        scores = [d['score'] for d in visible_dups]
        
        with col1:
            if scores:
                fig = px.histogram(
                    scores,
                    nbins=25,
                    title="Score Distribution",
                    labels={'value': 'Similarity', 'count': 'Count'},
                    color_discrete_sequence=['#6366f1']
                )
                fig.add_vline(
                    x=active_thresh,
                    line_dash="dash",
                    line_color="#10b981",
                    annotation_text="Threshold"
                )
                fig.update_layout(
                    plot_bgcolor='rgba(15, 15, 35, 0.5)',
                    paper_bgcolor='rgba(0, 0, 0, 0)',
                    font=dict(color='#e2e8f0', family='Inter', size=11),
                    height=300
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            method_counts = pd.Series([d['method'] for d in visible_dups]).value_counts()
            fig = px.pie(
                values=method_counts.values,
                names=method_counts.index,
                title="Detection Methods",
                color_discrete_sequence=['#6366f1', '#8b5cf6', '#ec4899']
            )
            fig.update_layout(
                plot_bgcolor='rgba(15, 15, 35, 0.5)',
                paper_bgcolor='rgba(0, 0, 0, 0)',
                font=dict(color='#e2e8f0', family='Inter', size=11),
                height=300
            )
            st.plotly_chart(fig, use_container_width=True)

# ==================== MANAGER TAB ====================
with tabs[1]:
    if st.session_state.duplicates:
        st.markdown("### Threshold Control")
        
        col_slider, col_info = st.columns([4, 1])
        
        with col_slider:
            new_thresh = st.slider(
                "Similarity Threshold",
                min_value=0.60,
                max_value=0.99,
                value=st.session_state.current_slider_val,
                step=0.01,
                label_visibility="collapsed"
            )
            if new_thresh != st.session_state.current_slider_val:
                st.session_state.current_slider_val = new_thresh
                st.rerun()
        
        with col_info:
            st.metric("Active", f"{st.session_state.current_slider_val:.0%}")
        
        active_dups = [d for d in st.session_state.duplicates if d['score'] >= st.session_state.current_slider_val]
        clusters = organize_clusters(active_dups)
        
        st.info(f"📦 {len(clusters)} groups • {len(active_dups)} pairs")
        
        # Actions
        col1, col2, col3, col4 = st.columns(4)
        
        if col1.button("✅ Select All", use_container_width=True):
            for c in clusters:
                for d in c['duplicates']:
                    st.session_state.deletion_queue.add(d['path'])
            st.rerun()
        
        if col2.button("❌ Clear", use_container_width=True):
            st.session_state.deletion_queue.clear()
            st.rerun()
        
        if col3.button("💾 Save", use_container_width=True):
            save_session_state()
            st.success("Saved!")
        
        if st.session_state.deletion_queue:
            if col4.button(
                f"🗑️ Delete ({len(st.session_state.deletion_queue)})",
                type="primary",
                use_container_width=True
            ):
                deleted = 0
                progress_bar = st.progress(0)
                total = len(st.session_state.deletion_queue)
                
                for i, f in enumerate(list(st.session_state.deletion_queue)):
                    try:
                        os.remove(f)
                        st.session_state.deletion_queue.discard(f)
                        deleted += 1
                    except:
                        pass
                    progress_bar.progress((i + 1) / total)
                
                st.session_state.duplicates = [
                    d for d in st.session_state.duplicates 
                    if os.path.exists(d['file1']) and os.path.exists(d['file2'])
                ]
                
                st.success(f"✓ Deleted {deleted} files")
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
            <div class='info-card'>
                <h4 style='color: #6366f1; font-family: "Space Grotesk", sans-serif; margin-bottom: 1rem;'>
                    Group {start + i + 1}
                </h4>
            </div>
            """, unsafe_allow_html=True)
            
            col_orig, col_dups = st.columns([1, 3])
            
            with col_orig:
                st.markdown("**Original**")
                try:
                    st.image(cluster['original'], use_container_width=True)
                    st.caption(f"{get_short_path(cluster['original'])}")
                except:
                    st.error("Load failed")
            
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
                                f'<span class="similarity-badge {badge_class}">{score_pct:.0f}%</span>',
                                unsafe_allow_html=True
                            )
                            c.caption(f"{get_short_path(dup['path'])}")
                            
                            is_selected = c.checkbox(
                                "Delete",
                                key=f"del_{start+i}_{idx}",
                                value=dup['path'] in st.session_state.deletion_queue
                            )
                            
                            if is_selected:
                                st.session_state.deletion_queue.add(dup['path'])
                            else:
                                st.session_state.deletion_queue.discard(dup['path'])
                        except:
                            c.error("Error")
            
            st.markdown("<br>", unsafe_allow_html=True)
        
        # Pagination
        col_prev, col_center, col_next = st.columns([1, 2, 1])
        
        with col_prev:
            if st.session_state.page > 0:
                if st.button("← Prev", use_container_width=True):
                    st.session_state.page -= 1
                    st.rerun()
        
        with col_center:
            st.markdown(f"<div style='text-align: center; padding-top: 0.5rem; color: #94a3b8;'>Page {st.session_state.page + 1} / {total_pages}</div>", unsafe_allow_html=True)
        
        with col_next:
            if end < len(clusters):
                if st.button("Next →", use_container_width=True):
                    st.session_state.page += 1
                    st.rerun()
    else:
        st.markdown("""
        <div class='info-card' style='text-align: center;'>
            <h3 style='color: #6366f1; font-family: "Space Grotesk", sans-serif;'>
                No Duplicates
            </h3>
            <p style='color: #94a3b8;'>Run a scan to find duplicates</p>
        </div>
        """, unsafe_allow_html=True)

# ==================== SEARCH TAB ====================
with tabs[2]:
    st.markdown("### Image Search")
    
    col_upload, col_settings = st.columns([2, 1])
    
    with col_upload:
        uploaded = st.file_uploader(
            "Upload image",
            type=['png', 'jpg', 'jpeg', 'bmp', 'webp'],
            label_visibility="collapsed"
        )
    
    with col_settings:
        query_threshold = st.slider(
            "Threshold",
            0.60, 0.99,
            st.session_state.current_slider_val,
            0.01,
            key="query_thresh"
        )
        max_results = st.number_input("Max Results", 1, 50, 10)
    
    if uploaded and st.session_state.detector:
        with open(config.TEMP_QUERY_FILE, "wb") as f:
            f.write(uploaded.getbuffer())
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(config.TEMP_QUERY_FILE, caption="Query Image", use_container_width=True)
        
        with st.spinner("Searching..."):
            results = st.session_state.detector.find_matches_for_file(
                config.TEMP_QUERY_FILE,
                threshold=query_threshold
            )
        
        if results:
            st.success(f"Found {len(results)} matches")
            
            results = results[:max_results]
            
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
                                    f'<span class="similarity-badge {badge_class}">{score_pct:.0f}%</span>',
                                    unsafe_allow_html=True
                                )
                                st.caption(get_short_path(res['path']))
                            except:
                                st.error("Load error")
        else:
            st.warning(f"No matches at {query_threshold:.0%}")
    
    elif not st.session_state.detector:
        st.info("Run a scan to enable search")

# ==================== ANALYTICS TAB ====================
with tabs[3]:
    st.markdown("### Analytics")
    
    if st.session_state.duplicates:
        active_thresh = st.session_state.current_slider_val
        visible_dups = [d for d in st.session_state.duplicates if d['score'] >= active_thresh]
        
        col1, col2, col3 = st.columns(3)
        
        scores = [d['score'] for d in visible_dups]
        
        with col1:
            st.metric("Mean", f"{sum(scores)/len(scores):.3f}" if scores else "N/A")
            st.metric("Median", f"{sorted(scores)[len(scores)//2]:.3f}" if scores else "N/A")
        
        with col2:
            st.metric("Min", f"{min(scores):.3f}" if scores else "N/A")
            st.metric("Max", f"{max(scores):.3f}" if scores else "N/A")
        
        with col3:
            clusters = organize_clusters(visible_dups)
            avg_size = sum(len(c['duplicates']) for c in clusters) / len(clusters) if clusters else 0
            st.metric("Avg Group", f"{avg_size:.1f}")
            st.metric("Groups", len(clusters))
        
        st.markdown("---")
        
        st.markdown("### Data Table")
        
        df_details = pd.DataFrame([
            {
                'File 1': get_short_path(d['file1']),
                'File 2': get_short_path(d['file2']),
                'Score': f"{d['score']:.3f}",
                'Method': d['method'],
                'Marked': '✓' if d['file2'] in st.session_state.deletion_queue else ''
            }
            for d in visible_dups
        ])
        
        st.dataframe(df_details, use_container_width=True, height=400)
        
    else:
        st.markdown("""
        <div class='info-card' style='text-align: center;'>
            <h3 style='color: #6366f1; font-family: "Space Grotesk", sans-serif;'>
                No Data
            </h3>
            <p style='color: #94a3b8;'>Run a scan to view analytics</p>
        </div>
        """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown(f"""
<div style='text-align: center; color: #64748b; padding: 1.5rem; font-family: "Inter", sans-serif; font-size: 0.875rem;'>
    <div style='margin-bottom: 0.5rem; color: #6366f1; font-weight: 600; font-family: "Space Grotesk", sans-serif;'>
        MIRROR OF MAYA
    </div>
    <div>Near-Duplicate Detection System</div>
    <div style='margin-top: 0.5rem; opacity: 0.6;'>{datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
</div>
""", unsafe_allow_html=True)