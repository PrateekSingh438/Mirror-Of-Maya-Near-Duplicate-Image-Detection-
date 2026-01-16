import streamlit as st
import os
import time
import pandas as pd
import plotly.express as px
from sklearn.decomposition import PCA
import networkx as nx
from engine import DuplicateDetector
from evaluate import calculate_metrics
import config
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
def get_dir_size(start_path='.'):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
    return total_size / (1024 * 1024)

def auto_generate_ground_truth(folder_path):
    from collections import defaultdict
    id_map = defaultdict(list)
    
    for root, _, filenames in os.walk(folder_path):
        for f in filenames:
            if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                file_id = os.path.splitext(f)[0]
                full_path = os.path.join(root, f)
                id_map[file_id].append(full_path)
    
    gt_pairs = []
    for file_id, paths in id_map.items():
        if len(paths) > 1:
            for i in range(len(paths)):
                for j in range(i + 1, len(paths)):
                    gt_pairs.append(tuple(sorted((paths[i], paths[j]))))
    return gt_pairs

def group_duplicates_into_clusters(duplicates_list):
    g = nx.Graph()
    for item in duplicates_list:
        g.add_edge(item['file1'], item['file2'])
    
    clusters = []
    for component in nx.connected_components(g):
        if len(component) > 1:
            clusters.append(list(component))
    return clusters

st.set_page_config(page_title="Mirror of Maya", layout="wide", page_icon="")

if 'detector' not in st.session_state:
    st.session_state.detector = None
if 'duplicates' not in st.session_state:
    st.session_state.duplicates = []
if 'deletion_queue' not in st.session_state:
    st.session_state.deletion_queue = set()

with st.sidebar:
    st.header("System Settings")
    dataset_path = st.text_input("Dataset Path", value="./dataset_copydays")
    threshold_pct = st.slider("Similarity Threshold (%)", 50, 100, 85)
    threshold_val = threshold_pct / 100.0
    
    st.divider()
    if st.button("Reload / Rescan Database", type="primary"):
        st.session_state.detector = DuplicateDetector()
        st.session_state.detector.bulk_index(dataset_path)
        st.session_state.duplicates = st.session_state.detector.find_duplicates(threshold=threshold_val)
        st.success(f"Index Updated! Found {len(st.session_state.duplicates)} pairs.")
        st.rerun()

st.title("Mirror of Maya")
st.markdown("Intelligent Deduplication & Analytics Engine")

tab_analysis, tab_visual, tab_action, tab_query = st.tabs([
    "Metrics & Report", 
    "Galaxy Cluster (Visual)", 
    "Action Queue (Clusters)", 
    "Query Tool"
])

with tab_analysis:
    if not st.session_state.duplicates:
        st.info("Click Reload Database in the sidebar to start.")
    else:
        original_mb = get_dir_size(dataset_path)
        wasted_size_mb = 0
        
        seen_files = set()
        for dup in st.session_state.duplicates:
            if dup['file2'] not in seen_files:
                try: 
                    wasted_size_mb += os.path.getsize(dup['file2']) / (1024 * 1024)
                    seen_files.add(dup['file2'])
                except:
                    pass
        
        optimized_mb = original_mb - wasted_size_mb
        pct_saved = (wasted_size_mb / original_mb * 100) if original_mb > 0 else 0
        
        ground_truth = auto_generate_ground_truth(dataset_path)
        f1 = calculate_metrics([(d['file1'], d['file2']) for d in st.session_state.duplicates], ground_truth) if ground_truth else 0.0
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Storage", f"{original_mb:.2f} MB")
        col2.metric("Potential Savings", f"{wasted_size_mb:.2f} MB", delta=f"{pct_saved:.1f}%")
        col3.metric("Duplicate Pairs", len(st.session_state.duplicates))
        col4.metric("Model F1 Score", f"{f1:.4f}")

with tab_visual:
    st.header("Image Embedding Clusters")
    st.write("Visualizing the model embedding space.")
    
    if st.session_state.detector and st.session_state.detector.index.ntotal > 0:
        if st.button("Generate Galaxy Plot"):
            with st.spinner("Reducing dimensions with PCA..."):
                ntotal = st.session_state.detector.index.ntotal
                limit = min(ntotal, 5000) 
                
                vectors = st.session_state.detector.index.reconstruct_n(0, limit)
                filenames = [os.path.basename(f) for f in st.session_state.detector.stored_files[:limit]]
                
                pca = PCA(n_components=2)
                vecs_2d = pca.fit_transform(vectors)
                
                df = pd.DataFrame(vecs_2d, columns=["x", "y"])
                df["filename"] = filenames
                
                fig = px.scatter(df, x="x", y="y", hover_data=["filename"], 
                                title=f"Galaxy View of {limit} Images",
                                color_discrete_sequence=["#00CC96"])
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Please scan the database first.")

with tab_action:
    st.header("Review & Delete Clusters")
    st.write("Similar images are grouped together.")
    
    if st.session_state.duplicates:
        clusters = group_duplicates_into_clusters(st.session_state.duplicates)
        st.info(f"Identified {len(clusters)} unique groups of duplicates.")

        page_size = 5
        if 'page' not in st.session_state:
            st.session_state.page = 0
        start_idx = st.session_state.page * page_size
        end_idx = start_idx + page_size
        current_clusters = clusters[start_idx:end_idx]
        
        for i, cluster in enumerate(current_clusters):
            cluster.sort()
            
            with st.container(border=True):
                st.markdown(f"Group {start_idx + i + 1}")
                cols = st.columns(min(len(cluster), 5))
                
                for idx, file_path in enumerate(cluster):
                    col_idx = idx % 5
                    with cols[col_idx]:
                        fname = os.path.basename(file_path)
                        st.image(file_path, use_container_width=True)
                        st.caption(fname)
                        
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
                success_count = 0
                for file_path in list(st.session_state.deletion_queue):
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            success_count += 1
                            st.session_state.deletion_queue.discard(file_path)
                    except Exception as e:
                        st.error(f"Failed to delete {file_path}: {e}")
                
                st.success(f"Successfully deleted {success_count} files!")
                st.session_state.duplicates = []
                time.sleep(2)
                st.rerun()
    else:
        st.info("No duplicates found yet. Reload the database.")

with tab_query:
    st.header("Search Single Image")
    uploaded_file = st.file_uploader("Upload Query Image", type=["jpg", "png"])
    if uploaded_file and st.session_state.detector:
        temp_path = "temp_query.jpg"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        results = st.session_state.detector.find_matches_for_file(temp_path, threshold=threshold_val)
        st.image(temp_path, width=200, caption="Query")
        st.write("---")
        if results:
            cols = st.columns(len(results))
            for idx, res in enumerate(results):
                with cols[idx]:
                    st.image(res['path'], caption=f"{res['score']*100:.1f}% Match")
        else:
            st.info("No matches found.")
