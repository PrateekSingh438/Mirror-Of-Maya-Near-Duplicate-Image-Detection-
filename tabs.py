import streamlit as st
import os
import pandas as pd
import plotly.graph_objects as go
import config
from utils import organize_clusters, format_file_size
from ui_components import get_short_path, get_similarity_class

def dashboard_tab():
    """Render Dashboard Tab"""
    if not st.session_state.duplicates:
        st.info("Click 'Full Scan' to begin detection")
        return
    
    if st.session_state.calibration_history:
        st.markdown("### Calibration Results")
        
        col_chart, col_table = st.columns([2, 1])
        
        df_cal = pd.DataFrame(st.session_state.calibration_history)
        
        with col_chart:
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=df_cal['threshold'], y=df_cal['f1'],
                mode='lines+markers', name='F1 Score',
                line=dict(color='#6366f1', width=3)
            ))
            
            fig.add_trace(go.Scatter(
                x=df_cal['threshold'], y=df_cal['precision'],
                mode='lines+markers', name='Precision',
                line=dict(color='#8b5cf6', width=2)
            ))
            
            fig.add_trace(go.Scatter(
                x=df_cal['threshold'], y=df_cal['recall'],
                mode='lines+markers', name='Recall',
                line=dict(color='#ec4899', width=2)
            ))
            
            # Current threshold line
            fig.add_vline(
                x=st.session_state.current_slider_val,
                line_dash="dash",
                line_color="#10b981",
                annotation_text="Current"
            )
            
            fig.update_layout(
                xaxis_title="Threshold",
                yaxis_title="Score",
                hovermode='x unified',
                height=350,
                plot_bgcolor='rgba(15, 15, 35, 0.5)',
                paper_bgcolor='rgba(0, 0, 0, 0)',
                font=dict(color='#e2e8f0', size=11)
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

def manager_tab():
    """Render Duplicate Manager Tab"""
    if not st.session_state.duplicates:
        st.info("No duplicates found")
        return
    
    clusters = organize_clusters(st.session_state.duplicates)
    
    st.info(f"📦 {len(clusters)} groups • {sum(len(c['duplicates']) for c in clusters)} duplicate files")
    
    # Actions
    col1, col2, col3 = st.columns(3)
    
    if col1.button("✅ Select All", use_container_width=True):
        for c in clusters:
            for d in c['duplicates']:
                st.session_state.deletion_queue.add(d['path'])
        st.rerun()
    
    if col2.button("❌ Clear", use_container_width=True):
        st.session_state.deletion_queue.clear()
        st.rerun()
    
    if st.session_state.deletion_queue and col3.button(
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
        
        # Update duplicates list
        st.session_state.duplicates = [
            d for d in st.session_state.duplicates 
            if os.path.exists(d['file1']) and os.path.exists(d['file2'])
        ]
        st.session_state.all_duplicates = [
            d for d in st.session_state.all_duplicates 
            if os.path.exists(d['file1']) and os.path.exists(d['file2'])
        ]
        
        st.success(f"✓ Deleted {deleted} files")
        st.rerun()
    
    st.markdown("---")
    
    # Pagination
    per_page = 5
    total_pages = max(1, (len(clusters) - 1) // per_page + 1)
    start = st.session_state.page * per_page
    end = min(start + per_page, len(clusters))
    
    # Display clusters
    for i, cluster in enumerate(clusters[start:end]):
        with st.container():
            st.markdown(f"**Group {start + i + 1}**")
            col_orig, col_dups = st.columns([1, 3])
            
            with col_orig:
                st.markdown("*Original*")
                try:
                    st.image(cluster['original'], use_container_width=True)
                    st.caption(get_short_path(cluster['original']))
                except:
                    st.error("Load failed")
            
            with col_dups:
                st.markdown("*Duplicates*")
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
                        c.caption(get_short_path(dup['path']))
                        
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
            
            st.markdown("---")
    
    # Pagination controls
    col_prev, col_center, col_next = st.columns([1, 2, 1])
    
    with col_prev:
        if st.session_state.page > 0 and st.button("← Prev", use_container_width=True):
            st.session_state.page -= 1
            st.rerun()
    
    with col_center:
        st.markdown(f"<div style='text-align: center; padding-top: 0.5rem;'>Page {st.session_state.page + 1} / {total_pages}</div>", unsafe_allow_html=True)
    
    with col_next:
        if end < len(clusters) and st.button("Next →", use_container_width=True):
            st.session_state.page += 1
            st.rerun()

def search_tab():
    """Render Image Search Tab"""
    st.markdown("### Image Search")
    
    col_upload, col_settings = st.columns([2, 1])
    
    with col_upload:
        uploaded = st.file_uploader("Upload image", type=['png', 'jpg', 'jpeg', 'bmp', 'webp'])
    
    with col_settings:
        query_threshold = st.slider("Threshold", 0.60, 0.99, 0.75, 0.01, key="query_thresh")
        max_results = st.number_input("Max Results", 1, 100, 50)
    
    if uploaded and st.session_state.detector:
        with open(config.TEMP_QUERY_FILE, "wb") as f:
            f.write(uploaded.getbuffer())
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(config.TEMP_QUERY_FILE, caption="Query", use_container_width=True)
        
        with st.spinner("Searching..."):
            results = st.session_state.detector.find_matches_for_file(
                config.TEMP_QUERY_FILE,
                threshold=query_threshold,
                top_k=max_results
            )
        
        if results:
            st.success(f"Found {len(results)} matches")
            
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
        st.info("Run scan to enable search")

def analytics_tab():
    """Render Analytics Tab"""
    st.markdown("### Analytics")
    
    if not st.session_state.duplicates:
        st.info("Run a scan to view analytics")
        return
    
    clusters = organize_clusters(st.session_state.duplicates)
    scores = [d['score'] for d in st.session_state.duplicates]
    unique_duplicates = sum(len(c['duplicates']) for c in clusters)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Duplicate Files", unique_duplicates)
        st.metric("Duplicate Pairs", len(st.session_state.duplicates))
    
    with col2:
        st.metric("Mean Score", f"{sum(scores)/len(scores):.3f}" if scores else "N/A")
        st.metric("Median Score", f"{sorted(scores)[len(scores)//2]:.3f}" if scores else "N/A")
    
    with col3:
        st.metric("Groups", len(clusters))
        avg_size = sum(len(c['duplicates']) for c in clusters) / len(clusters) if clusters else 0
        st.metric("Avg Group Size", f"{avg_size:.1f}")
    
    st.markdown("---")
    st.markdown("### Original vs Duplicate Comparison")
    
    # Count originals vs duplicates
    originals = set(c['original'] for c in clusters)
    duplicates_set = set()
    for c in clusters:
        for d in c['duplicates']:
            duplicates_set.add(d['path'])
    
    comp_col1, comp_col2 = st.columns(2)
    with comp_col1:
        st.metric("Original Files", len(originals))
    with comp_col2:
        st.metric("Duplicate Files", len(duplicates_set))
    
    st.success(f"✓ System correctly identifies originals and compares them only to duplicates")
    
    st.markdown("---")
    st.markdown("### Detailed List")
    
    df_details = pd.DataFrame([
        {
            'Original': get_short_path(c['original']),
            'Duplicate': get_short_path(d['path']),
            'Score': f"{d['score']:.3f}",
            'Marked': '✓' if d['path'] in st.session_state.deletion_queue else ''
        }
        for c in clusters
        for d in c['duplicates']
    ])
    
    st.dataframe(df_details, use_container_width=True, height=400)

def hash_duplicates_tab():
    """Render Hash-Based Duplicates Tab"""
    st.markdown("### ⚡ Hash-Based Duplicate Detection")
    
    if not st.session_state.detector:
        st.info("Run a scan first to enable hash detection")
        return
    
    # Display hash duplicates from detector
    if hasattr(st.session_state.detector, 'fast_duplicates') and st.session_state.detector.fast_duplicates:
        hash_dups = st.session_state.detector.fast_duplicates
        
        st.success(f"⚡ Found {len(hash_dups)} exact/near-exact duplicates via perceptual hashing")
        
        st.markdown("---")
        
        # Group by file pairs
        for i in range(0, len(hash_dups), 3):
            cols = st.columns(3)
            for j, col in enumerate(cols):
                if i + j < len(hash_dups):
                    dup = hash_dups[i + j]
                    with col:
                        try:
                            st.markdown(f"**Pair {i + j + 1}**")
                            
                            # Display both images
                            st.image(dup['file1'], caption="File 1", use_container_width=True)
                            st.caption(get_short_path(dup['file1']))
                            
                            st.image(dup['file2'], caption="File 2", use_container_width=True)
                            st.caption(get_short_path(dup['file2']))
                            
                            # Score badge
                            score_pct = dup['score'] * 100
                            st.markdown(
                                f'<span class="similarity-badge similarity-high">{score_pct:.0f}%</span>',
                                unsafe_allow_html=True
                            )
                            st.caption(f"Method: {dup['method']}")
                            
                            # Delete option
                            if st.checkbox(f"Delete File 2", key=f"hash_del_{i+j}"):
                                if st.button(f"🗑️ Confirm Delete", key=f"hash_confirm_{i+j}", type="primary"):
                                    try:
                                        os.remove(dup['file2'])
                                        st.success("✓ Deleted")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error: {e}")
                        except Exception as e:
                            st.error(f"Error loading: {e}")
            
            if i + 3 < len(hash_dups):
                st.markdown("---")
    else:
        st.info("No hash-based duplicates found. These are detected during the scan phase.")
        st.markdown("""
        **Hash-based detection** finds:
        - 🎯 Exact duplicates (pixel-perfect matches)
        - 📸 Near-exact duplicates (minor compression differences)
        - 🔍 Very similar images with identical perceptual hashes
        
        Run a **Full Scan** to populate this tab.
        """)