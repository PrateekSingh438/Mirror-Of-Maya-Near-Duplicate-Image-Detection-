import streamlit as st
import os
import time
import pandas as pd
import plotly.express as px
from sklearn.decomposition import PCA
import networkx as nx
from engine import DuplicateDetector
from evaluate import calculate_metrics, analyze_match_types
from utils import (
    get_dir_size, auto_generate_ground_truth, 
    calculate_wasted_space, is_original_file
)
import config

os.environ["KMP_DUPLICATE_LIB_OK"] = config.ENV_KMP_DUPLICATE_LIB

def group_duplicates_into_clusters(duplicates_list):
    
    if not duplicates_list:
        return []
    
    g = nx.Graph()
    for item in duplicates_list:
        g.add_edge(item['file1'], item['file2'])
    
    clusters = []
    for component in nx.connected_components(g):
        if len(component) > 1:
            clusters.append(list(component))
    return clusters

# Page Configuration
st.set_page_config(
    page_title=config.PAGE_TITLE, 
    layout=config.LAYOUT, 
    page_icon=config.PAGE_ICON
)

# Session State Initialization
if 'detector' not in st.session_state:
    st.session_state.detector = None
if 'duplicates' not in st.session_state:
    st.session_state.duplicates = []
if 'deletion_queue' not in st.session_state:
    st.session_state.deletion_queue = set()

# Sidebar Configuration
with st.sidebar:
    st.header("Settings")
    
    selected_label = st.selectbox("Select Model", list(config.MODEL_OPTIONS.keys()))
    new_model_id = config.MODEL_OPTIONS[selected_label]
    
    if config.MODEL_ID != new_model_id:
        config.MODEL_ID = new_model_id
        st.session_state.detector = DuplicateDetector()
        st.session_state.duplicates = []
        st.sidebar.info(f"Switched to {selected_label}. Please Scan.")

    dataset_path = st.text_input("Dataset Path", value=config.DATASET_PATH)
    threshold_pct = st.slider(
        "Similarity Threshold (%)", 
        50, 100, 
        config.DEFAULT_THRESHOLD_PERCENT
    )
    threshold_val = threshold_pct / 100.0
    
    st.divider()
    
    if st.button("Fresh Scan", type="primary"):
        with st.spinner("Processing images..."):
            st.session_state.detector = DuplicateDetector()
            st.session_state.detector.bulk_index(dataset_path)
            st.session_state.duplicates = st.session_state.detector.find_duplicates(
                threshold=threshold_val
            )
            st.success("Scan Complete!")
            st.rerun()

# Main Title
st.title(config.PAGE_TITLE)
st.markdown("Intelligent Deduplication & Analytics Engine")

# Tabs
tab_analysis, tab_visual, tab_action, tab_query = st.tabs([
    "Metrics & Report", 
    "Galaxy Cluster (Visual)", 
    "Action Queue (Clusters)", 
    "Query Tool"
])

# Tab 1: Analysis & Metrics
with tab_analysis:
    if not st.session_state.duplicates:
        st.info("Click Fresh Scan in the sidebar to start.")
    else:
        original_mb = get_dir_size(dataset_path)
        wasted_size_mb = calculate_wasted_space(st.session_state.duplicates)
        optimized_mb = original_mb - wasted_size_mb
        pct_saved = (wasted_size_mb / original_mb * 100) if original_mb > 0 else 0
        
        ground_truth = auto_generate_ground_truth(dataset_path)
        f1 = calculate_metrics(
            [(d['file1'], d['file2']) for d in st.session_state.duplicates], 
            ground_truth
        ) if ground_truth else 0.0
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Storage", f"{original_mb:.2f} MB")
        col2.metric("Potential Savings", f"{wasted_size_mb:.2f} MB", delta=f"{pct_saved:.1f}%") 
        col3.metric("Duplicate Pairs", len(st.session_state.duplicates))
        col4.metric("Model F1 Score", f"{f1:.4f}")

        st.divider()
        st.subheader("Quality Check")
        
        analysis = analyze_match_types(st.session_state.duplicates)
        
        if analysis['total'] > 0:
            c_a, c_b = st.columns(2)
            c_a.metric(
                label="Originals Recovered", 
                value=f"{analysis['recovery']} pairs",
                delta=f"{analysis['recovery_pct']:.1f}% of total"
            )
            c_b.metric(
                label="Cross-Matches", 
                value=f"{analysis['cross']} pairs", 
                delta=f"{analysis['cross_pct']:.1f}% of total",
                delta_color="inverse"
            )
            if analysis['cross_pct'] > 50:
                st.warning("Warning: High cross-match rate.")
            else:
                st.success("System is anchoring to originals correctly.")

# Tab 2: Visualization
with tab_visual:
    st.header("Image Embedding Clusters")
    
    if st.session_state.detector and st.session_state.detector.index.ntotal > 0:
        if st.button("Generate Galaxy Plot"):
            with st.spinner("Reducing dimensions with PCA..."):
                ntotal = st.session_state.detector.index.ntotal
                limit = min(ntotal, config.MAX_GALAXY_PLOT_IMAGES)
                
                vectors = st.session_state.detector.index.reconstruct_n(0, limit)
                filenames = [
                    os.path.basename(f) 
                    for f in st.session_state.detector.stored_files[:limit]
                ]
                
                pca = PCA(n_components=2)
                vecs_2d = pca.fit_transform(vectors)
                
                df = pd.DataFrame(vecs_2d, columns=["x", "y"])
                df["filename"] = filenames
                
                fig = px.scatter(
                    df, x="x", y="y", 
                    hover_data=["filename"], 
                    title=f"Galaxy View of {limit} Images",
                    color_discrete_sequence=[config.GALAXY_COLOR]
                )
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Please scan the database first.")

# Tab 3: Action & Deletion
with tab_action:
    st.header("Review & Delete Clusters")
    
    if st.session_state.duplicates:
        clusters = group_duplicates_into_clusters(st.session_state.duplicates)
        st.info(f"Identified {len(clusters)} unique groups of duplicates.")

        if 'page' not in st.session_state:
            st.session_state.page = 0
        
        start_idx = st.session_state.page * config.CLUSTERS_PER_PAGE
        end_idx = start_idx + config.CLUSTERS_PER_PAGE
        current_clusters = clusters[start_idx:end_idx]
        
        for i, cluster in enumerate(current_clusters):
            cluster.sort()
            with st.container(border=True):
                st.markdown(f"Group {start_idx + i + 1}")
                cols = st.columns(min(len(cluster), config.MAX_IMAGES_PER_ROW))
                
                for idx, file_path in enumerate(cluster):
                    col_idx = idx % config.MAX_IMAGES_PER_ROW
                    with cols[col_idx]:
                        fname = os.path.basename(file_path)
                        st.image(file_path, use_container_width=True)
                        st.caption(fname)
                        
                        for d in st.session_state.duplicates:
                            if d['file1'] == file_path or d['file2'] == file_path:
                                if d.get('method') == "pHash":
                                    st.markdown("**pHash Match**")
                                    break
                                    
                        is_selected = file_path in st.session_state.deletion_queue
                        if st.checkbox("Delete", value=is_selected, key=f"del_{start_idx+i}_{idx}"):
                            st.session_state.deletion_queue.add(file_path)
                        else:
                            st.session_state.deletion_queue.discard(file_path)

        c1, c2, c3 = st.columns([1, 2, 1])
        if st.session_state.page > 0:
            if c1.button("Previous"):
                st.session_state.page -= 1
        if end_idx < len(clusters):
            if c3.button("Next"):
                st.session_state.page += 1
            
        st.divider()
        pending_count = len(st.session_state.deletion_queue)
        if pending_count > 0:
            st.warning(f"{pending_count} files selected for deletion.")
            if st.button(f"EXECUTE DELETION ({pending_count} Files)"):
                for file_path in list(st.session_state.deletion_queue):
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            st.session_state.deletion_queue.discard(file_path)
                    except Exception:
                        pass
                st.success("Deleted!")
                st.session_state.duplicates = []
                time.sleep(1)
                st.rerun()
    else:
        st.info("No duplicates found yet. Reload the database.")

# Tab 4: Query Tool
with tab_query:
    st.header("Search Single Image")
    uploaded_file = st.file_uploader("Upload Query Image", type=["jpg", "png"])
    
    if uploaded_file and st.session_state.detector:
        with open(config.TEMP_QUERY_FILE, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        results = st.session_state.detector.find_matches_for_file(
            config.TEMP_QUERY_FILE, 
            threshold=threshold_val
        )
        st.image(config.TEMP_QUERY_FILE, width=200, caption="Query")
        st.write("---")
        
        if results:
            cols = st.columns(len(results))
            for idx, res in enumerate(results):
                with cols[idx]:
                    st.image(res['path'], caption=f"{res['score']*100:.1f}% Match")
        else:
            st.info("No matches found.")