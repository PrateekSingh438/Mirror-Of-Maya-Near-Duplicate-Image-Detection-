import streamlit as st
from datetime import datetime
import config
from ui_components import render_sidebar, render_header, apply_custom_css
from tabs import dashboard_tab, manager_tab, search_tab, analytics_tab, hash_duplicates_tab
from utils import format_file_size, organize_clusters, calculate_wasted_space
from session_manager import initialize_session_state, load_session_state

# Page Configuration
st.set_page_config(
    page_title="Mirror of Maya", 
    layout=config.LAYOUT, 
    page_icon="🔍",
    initial_sidebar_state="expanded"
)

# Apply Custom Styling
apply_custom_css()

# Initialize Session State
initialize_session_state()
load_session_state()

# Render Sidebar
render_sidebar()

# Render Header
render_header()

# Dynamic Threshold Control with Live Metrics
if st.session_state.detector and st.session_state.all_duplicates:
    from ui_components import render_threshold_control
    render_threshold_control()

# Status Bar
if st.session_state.detector:
    visible_dups = st.session_state.duplicates
    
    # Use clustering mode from session state
    clustering_mode = st.session_state.get('clustering_mode', config.CLUSTERING_MODE)
    clusters = organize_clusters(visible_dups, mode=clustering_mode)
    
    unique_duplicates = sum(len(c['duplicates']) for c in clusters)
    waste = calculate_wasted_space(visible_dups)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("DUPLICATE FILES", f"{unique_duplicates:,}")
    col2.metric("WASTED SPACE", format_file_size(waste * 1024 * 1024))
    col3.metric("F1 SCORE", f"{st.session_state.f1_score:.4f}")
    col4.metric("THRESHOLD", f"{st.session_state.current_slider_val:.2f}")

st.markdown("---")

# Main Tabs
tabs = st.tabs(["📊 Dashboard", "🗂️ Manager", "🔎 Search", "📈 Analytics", "⚡ Hash Duplicates"])

with tabs[0]:
    dashboard_tab()

with tabs[1]:
    manager_tab()

with tabs[2]:
    search_tab()

with tabs[3]:
    analytics_tab()

with tabs[4]:
    hash_duplicates_tab()

# Footer
st.markdown("---")
st.markdown(f"""
<div style='text-align: center; font-family: "Inter", sans-serif; color: #64748b; padding: 1.5rem; font-size: 0.875rem;'>
    <div style='margin-bottom: 0.5rem; color: #6366f1; font-weight: 600; font-family: "Space Grotesk", sans-serif;'>
        MIRROR OF MAYA
    </div>
    <div>Near-Duplicate Detection System</div>
    <div style='margin-top: 0.5rem; opacity: 0.6;'>{datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
</div>
""", unsafe_allow_html=True)