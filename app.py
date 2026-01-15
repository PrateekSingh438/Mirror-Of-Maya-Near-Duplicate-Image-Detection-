import streamlit as st
import os
import time
import pandas as pd
import plotly.express as px
from sklearn.decomposition import PCA
from engine import DuplicateDetector
from evaluate import calculate_metrics
import config

# --- HELPER FUNCTIONS ---
def get_dir_size(start_path='.'):
    """Calculates total size of a folder in MB"""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
    return total_size / (1024 * 1024)

def auto_generate_ground_truth(folder_path):
    files = sorted(os.listdir(folder_path))
    gt = []
    for f in files:
        if not f.lower().endswith(('.jpg', '.png')): continue
        if "_aug" in f or "_copy" in f:
            base = f.split("_aug")[0].split("_copy")[0] + os.path.splitext(f)[1]
            if base in files:
                gt.append((base, f))
    return gt

# --- PAGE CONFIG ---
st.set_page_config(page_title="Mirror of Maya: Pro", layout="wide", page_icon="🔮")

# --- SESSION STATE INITIALIZATION ---
if 'detector' not in st.session_state:
    st.session_state.detector = None
if 'duplicates' not in st.session_state:
    st.session_state.duplicates = []
if 'deletion_queue' not in st.session_state:
    st.session_state.deletion_queue = set()

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ System Settings")
    dataset_path = st.text_input("Dataset Path", value="./dataset")
    threshold_pct = st.slider("Similarity Threshold (%)", 50, 100, 92)
    threshold_val = threshold_pct / 100.0
    
    st.divider()
    if st.button("🔄 Reload / Rescan Database", type="primary"):
        st.session_state.detector = DuplicateDetector()
        st.session_state.detector.bulk_index(dataset_path)
        st.session_state.duplicates = st.session_state.detector.find_duplicates(threshold=threshold_val)
        st.success(f"Index Updated! Found {len(st.session_state.duplicates)} pairs.")
        st.rerun()

# --- MAIN APP ---
st.title("🔮 Mirror of Maya")
st.markdown("### Intelligent Deduplication & Analytics Engine")

# TABS
tab_analysis, tab_visual, tab_action, tab_query = st.tabs([
    "📊 Metrics & Report", 
    "🌌 Galaxy Cluster (Visual)", 
    "⚔️ Action Queue (Tinder)", 
    "🔍 Query Tool"
])

# --- TAB 1: METRICS ---
with tab_analysis:
    if not st.session_state.duplicates:
        st.info("👈 Click 'Reload Database' in the sidebar to start.")
    else:
        # Calculate Metrics
        original_mb = get_dir_size(dataset_path)
        wasted_size_mb = 0
        for dup in st.session_state.duplicates:
            try: wasted_size_mb += os.path.getsize(dup['file2']) / (1024 * 1024)
            except: pass
        
        optimized_mb = original_mb - wasted_size_mb
        pct_saved = (wasted_size_mb / original_mb * 100) if original_mb > 0 else 0
        
        # Ground Truth F1
        ground_truth = auto_generate_ground_truth(dataset_path)
        f1 = calculate_metrics([(d['file1'], d['file2']) for d in st.session_state.duplicates], ground_truth) if ground_truth else 0.0
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Storage", f"{original_mb:.2f} MB")
        col2.metric("Potential Savings", f"{wasted_size_mb:.2f} MB", delta=f"{pct_saved:.1f}%")
        col3.metric("Duplicate Pairs", len(st.session_state.duplicates))
        col4.metric("Model F1 Score", f"{f1:.4f}")

# --- TAB 2: GALAXY PLOT (FEATURE 3) ---
with tab_visual:
    st.header("🌌 Image Embedding Clusters")
    st.write("Visualizing the 'brain' of DINOv2. Similar images appear closer together.")
    
    if st.session_state.detector and st.session_state.detector.index.ntotal > 0:
        if st.button("Generate Galaxy Plot"):
            with st.spinner("Reducing dimensions with PCA..."):
                # 1. Extract Vectors from FAISS
                # FAISS IndexFlatIP stores vectors directly. We reconstruct them.
                ntotal = st.session_state.detector.index.ntotal
                # Limit to 2000 points for speed if dataset is huge
                limit = min(ntotal, 5000) 
                
                vectors = st.session_state.detector.index.reconstruct_n(0, limit)
                filenames = [os.path.basename(f) for f in st.session_state.detector.stored_files[:limit]]
                
                # 2. Run PCA (384 dims -> 2 dims)
                pca = PCA(n_components=2)
                vecs_2d = pca.fit_transform(vectors)
                
                # 3. Create DataFrame for Plotly
                df = pd.DataFrame(vecs_2d, columns=["x", "y"])
                df["filename"] = filenames
                
                # 4. Plot
                fig = px.scatter(df, x="x", y="y", hover_data=["filename"], 
                                title=f"Galaxy View of {limit} Images",
                                color_discrete_sequence=["#00CC96"])
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Please scan the database first.")

# --- TAB 3: ACTION QUEUE (FEATURE 1) ---
with tab_action:
    st.header("⚔️ Review & Delete")
    st.write("Select which version to keep. Changes are applied only when you click 'Execute'.")
    
    if st.session_state.duplicates:
        # Pagination to prevent lag
        page_size = 10
        if 'page' not in st.session_state: st.session_state.page = 0
        
        start_idx = st.session_state.page * page_size
        end_idx = start_idx + page_size
        current_batch = st.session_state.duplicates[start_idx:end_idx]
        
        # Display Batch
        for i, dup in enumerate(current_batch):
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 2, 1])
                
                # Images
                c1.image(dup['file1'], caption=f"Left: {os.path.basename(dup['file1'])}")
                c2.image(dup['file2'], caption=f"Right: {os.path.basename(dup['file2'])}")
                
                # Controls
                with c3:
                    st.write(f"**Similarity:** {dup['score']*100:.1f}%")
                    choice = st.radio("Action:", ["Keep Both", "Delete Left", "Delete Right"], key=f"act_{start_idx+i}")
                    
                    # Logic to queue deletion
                    if choice == "Delete Left":
                        st.session_state.deletion_queue.add(dup['file1'])
                        st.session_state.deletion_queue.discard(dup['file2'])
                    elif choice == "Delete Right":
                        st.session_state.deletion_queue.add(dup['file2'])
                        st.session_state.deletion_queue.discard(dup['file1'])
                    else:
                        st.session_state.deletion_queue.discard(dup['file1'])
                        st.session_state.deletion_queue.discard(dup['file2'])

        # Pagination Buttons
        col_p1, col_p2, col_p3 = st.columns([1, 2, 1])
        if st.session_state.page > 0:
            if col_p1.button("Previous Page"): st.session_state.page -= 1
        if end_idx < len(st.session_state.duplicates):
            if col_p3.button("Next Page"): st.session_state.page += 1
            
        st.divider()
        
        # Execution Button
        pending_count = len(st.session_state.deletion_queue)
        if pending_count > 0:
            st.error(f"⚠️ {pending_count} files marked for deletion.")
            if st.button(f"🗑️ EXECUTE DELETION ({pending_count} Files)"):
                success_count = 0
                for file_path in st.session_state.deletion_queue:
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            success_count += 1
                    except Exception as e:
                        st.error(f"Failed to delete {file_path}: {e}")
                
                st.success(f"Successfully deleted {success_count} files!")
                st.session_state.deletion_queue.clear()
                st.session_state.duplicates = [] # Force rescan
                time.sleep(2)
                st.rerun()

# --- TAB 4: QUERY TOOL (Existing) ---
with tab_query:
    st.header("Search Single Image")
    uploaded_file = st.file_uploader("Upload Query Image", type=["jpg", "png"])
    if uploaded_file and st.session_state.detector:
        temp_path = "temp_query.jpg"
        with open(temp_path, "wb") as f: f.write(uploaded_file.getbuffer())
        
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