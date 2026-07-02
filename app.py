import streamlit as st
from datetime import datetime
import config
from ui_components import (render_sidebar, render_header, apply_custom_css,
                           render_threshold_control, maybe_load_demo)
from tabs import (dashboard_tab, manager_tab, search_tab, analytics_tab,
                  hash_duplicates_tab, versus_tab, architecture_tab, _get_clusters)
from utils import format_file_size, calculate_wasted_space
from session_manager import (initialize_session_state, load_session_state,
                             recalculate_metrics)

# Page config
st.set_page_config(
    page_title=config.PAGE_TITLE,
    layout=config.LAYOUT,
    initial_sidebar_state="expanded"
)

# Apply styling
apply_custom_css()

# Initialize session
initialize_session_state()
load_session_state()

# With no scan yet, preload the built-in demo dataset (if bundled)
maybe_load_demo()

# Sidebar
render_sidebar()

# Header
render_header()

# Threshold control
if st.session_state.detector and st.session_state.all_duplicates:
    render_threshold_control()

# Status bar
if st.session_state.detector:
    clusters = _get_clusters()
    unique_duplicates = sum(len(c['duplicates']) for c in clusters)
    waste = calculate_wasted_space(clusters)
    metrics = recalculate_metrics(st.session_state.current_slider_val)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Duplicate files", f"{unique_duplicates:,}")
    col2.metric("Space used by copies", format_file_size(waste * 1024 * 1024))
    col3.metric("F1 score", f"{metrics['f1']:.4f}" if metrics else "N/A",
                help="Live score at the current threshold, measured on the "
                     "FULL ground truth. The Dashboard reports the stricter "
                     "held-out score." if metrics
                else "Needs a dataset with ground truth")
    col4.metric("Threshold", f"{st.session_state.current_slider_val:.2f}")

st.markdown("---")

# Tabs
tabs = st.tabs(["Dashboard", "Manager", "Search", "Analytics",
                "Exact Copies", "Compare", "How It Works"])

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

with tabs[5]:
    versus_tab()

with tabs[6]:
    architecture_tab()

# Footer
st.markdown("---")
st.markdown(f"""
<div style='text-align: center; color: #64748b; padding: 1.5rem; font-size: 0.875rem;'>
    <div style='margin-bottom: 0.5rem; color: #6366f1; font-weight: 600;'>
        MIRROR OF MAYA
    </div>
    <div>Near-duplicate image detection</div>
    <div style='margin-top: 0.5rem; opacity: 0.6;'>{datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
</div>
""", unsafe_allow_html=True)
