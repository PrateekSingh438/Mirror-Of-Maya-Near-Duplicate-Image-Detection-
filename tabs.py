import streamlit as st
import os
import pandas as pd
import plotly.graph_objects as go
import config
from utils import organize_clusters, format_file_size
from ui_components import get_short_path, get_similarity_class
import numpy as np
import base64


def dashboard_tab():  
    if not st.session_state.duplicates:
        st.markdown("""
        <div style='text-align: center; padding: 4rem 2rem; background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(236, 72, 153, 0.1)); border-radius: 1rem; border: 2px solid rgba(139, 92, 246, 0.3);'>
            <h2 style='color: #a855f7; font-family: Cinzel, serif; font-size: 2rem; margin-bottom: 1rem;'>The Mirror of Maya Awaits</h2>
            <p style='color: #94a3b8; font-family: Inter, sans-serif; font-size: 1.2rem;'>Click <strong>SCAN DATABASE</strong> in the sidebar to pierce through the veil of digital illusions</p>
            <p style='color: #64748b; font-family: Inter, sans-serif; margin-top: 1rem;'>Just as Maya creates a thousand forms from one truth, this system reveals the original soul beneath countless digital avatars</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    st.markdown("""
    <div style='text-align: center; margin-bottom: 2rem;'>
        <h2 style='background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
                   -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                   font-family: Cinzel, serif; font-size: 2.5rem; font-weight: 800;'>
            Mirror Of Maya: Digital Discernment Engine
        </h2>
        <p style='color: #94a3b8; font-family: Inter, sans-serif; font-size: 1.1rem;'>Cutting Through Illusions to Reveal Truth</p>
    </div>
    """, unsafe_allow_html=True)
    clustering_mode = st.session_state.get('clustering_mode', 'basename')
    clusters = organize_clusters(st.session_state.duplicates, mode=clustering_mode)
    unique_dups = sum(len(c['duplicates']) for c in clusters)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(139, 92, 246, 0.2)); 
                    padding: 1.5rem; border-radius: 1rem; border: 1px solid rgba(99, 102, 241, 0.3);'>
            <div style='color: #818cf8; font-family: Cinzel, serif; font-size: 0.875rem; font-weight: 600;'>ILLUSIONS PIERCED</div>
            <div style='color: #e2e8f0; font-family: Inter, sans-serif; font-size: 2rem; font-weight: 800; margin: 0.5rem 0;'>{unique_dups:,}</div>
            <div style='color: #94a3b8; font-family: Inter, sans-serif; font-size: 0.75rem;'>Digital avatars unmasked</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, rgba(168, 85, 247, 0.2), rgba(236, 72, 153, 0.2)); 
                    padding: 1.5rem; border-radius: 1rem; border: 1px solid rgba(168, 85, 247, 0.3);'>
            <div style='color: #c084fc; font-family: Cinzel, serif; font-size: 0.875rem; font-weight: 600;'>TRUTH CLUSTERS</div>
            <div style='color: #e2e8f0; font-family: Inter, sans-serif; font-size: 2rem; font-weight: 800; margin: 0.5rem 0;'>{len(clusters):,}</div>
            <div style='color: #94a3b8; font-family: Inter, sans-serif; font-size: 0.75rem;'>Original souls identified</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, rgba(236, 72, 153, 0.2), rgba(244, 114, 182, 0.2)); 
                    padding: 1.5rem; border-radius: 1rem; border: 1px solid rgba(236, 72, 153, 0.3);'>
            <div style='color: #f472b6; font-family: Cinzel, serif; font-size: 0.875rem; font-weight: 600;'>DISCERNMENT ACCURACY</div>
            <div style='color: #e2e8f0; font-family: Inter, sans-serif; font-size: 2rem; font-weight: 800; margin: 0.5rem 0;'>{st.session_state.f1_score:.1%}</div>
            <div style='color: #94a3b8; font-family: Inter, sans-serif; font-size: 0.75rem;'>F1 Score</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        avg_sim = np.mean([d['score'] for d in st.session_state.duplicates]) if st.session_state.duplicates else 0
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(5, 150, 105, 0.2)); 
                    padding: 1.5rem; border-radius: 1rem; border: 1px solid rgba(16, 185, 129, 0.3);'>
            <div style='color: #34d399; font-family: Cinzel, serif; font-size: 0.875rem; font-weight: 600;'>IMAGE SIMILARITY</div>
            <div style='color: #e2e8f0; font-family: Inter, sans-serif; font-size: 2rem; font-weight: 800; margin: 0.5rem 0;'>{avg_sim:.1%}</div>
            <div style='color: #94a3b8; font-family: Inter, sans-serif; font-size: 0.75rem;'>Average resemblance</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.session_state.calibration_history:
        df_cal = pd.DataFrame(st.session_state.calibration_history)
        
        #tabs for different visualizations
        viz_tabs = st.tabs(["Calibration Curves", "Score Distribution", "Detection Insights"])
        
        with viz_tabs[0]:
            _render_calibration_curves(df_cal)
        
        with viz_tabs[1]:
            _render_score_distribution()
        
        with viz_tabs[2]:
            _render_detection_insights(df_cal)

def _render_calibration_curves(df_cal):
    """Render main calibration curves"""
    st.markdown("### The Path of Discernment")
    st.markdown("*Watch how the Mirror of Maya's precision evolves across threshold levels*")
    
    col_chart, col_table = st.columns([2, 1])
    
    with col_chart:
        fig = go.Figure()
        
        # F1 Score
        fig.add_trace(go.Scatter(
            x=df_cal['threshold'], 
            y=df_cal['f1'],
            mode='lines+markers',
            name='F1 Score (Balance)',
            line=dict(color='#6366f1', width=4),
            marker=dict(size=10, symbol='diamond'),
            hovertemplate='<b>Threshold:</b> %{x:.2f}<br><b>F1:</b> %{y:.3f}<extra></extra>'
        ))
        
        # Optimal threshold marker
        optimal_idx = df_cal['f1'].idxmax()
        optimal_thresh = df_cal.loc[optimal_idx, 'threshold']
        optimal_f1 = df_cal.loc[optimal_idx, 'f1']
        
        fig.add_vline(
            x=optimal_thresh,
            line_dash="solid",
            line_color="#10b981",
            line_width=2,
            annotation_text=f"Optimal: {optimal_thresh:.2f}",
            annotation_position="top"
        )
        
        fig.add_trace(go.Scatter(
            x=[optimal_thresh],
            y=[optimal_f1],
            mode='markers',
            name='Optimal Point',
            marker=dict(size=20, color='#10b981', symbol='star'),
            showlegend=False
        ))
        
        fig.update_layout(
            xaxis_title="Threshold (Strictness Level)",
            yaxis_title="Score",
            hovermode='x unified',
            height=450,
            plot_bgcolor='rgba(15, 15, 35, 0.8)',
            paper_bgcolor='rgba(0, 0, 0, 0)',
            font=dict(color='#e2e8f0', size=12),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        st.plotly_chart(fig, width='stretch')
    
    with col_table:
        st.markdown("**Performance Metrics**")
        st.dataframe(
            df_cal[["threshold", "f1"]]
            .style.highlight_max(axis=0, subset=["f1"])
            .background_gradient(subset=['f1'], cmap='viridis')
            .format({
                'f1': '{:.3f}',
                'threshold': '{:.2f}'
            }),
            width='stretch',
            height=450
        )

def _render_score_distribution():
    """Render similarity score distributions"""
    st.markdown("### The Spectrum of Resemblance")
    st.markdown("*How similar are the detected avatars to their originals?*")
    
    scores = [d['score'] for d in st.session_state.duplicates]

    # Histogram
    fig = go.Figure()
    
    fig.add_trace(go.Histogram(
        x=scores,
        nbinsx=30,
        marker=dict(
            color='#a855f7',
            line=dict(color='#1e293b', width=1)
        ),
        hovertemplate='<b>Score Range:</b> %{x}<br><b>Count:</b> %{y}<extra></extra>'
    ))
    
    #Threshold
    fig.add_vline(
        x=st.session_state.current_slider_val,
        line_dash="dash",
        line_color="#10b981",
        line_width=2,
        annotation_text="Current Threshold"
    )
    
    fig.update_layout(
        title="Similarity Score Distribution",
        xaxis_title="Similarity Score",
        yaxis_title="Frequency",
        height=400,
        plot_bgcolor='rgba(15, 15, 35, 0.8)',
        paper_bgcolor='rgba(0, 0, 0, 0)',
        font=dict(color='#e2e8f0'),
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)

def _render_detection_insights(df_cal):
    """Render additional insights"""
    st.markdown("### Detection Insights")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Detection 
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df_cal['threshold'],
            y=df_cal['count'],
            mode='lines+markers',
            fill='tozeroy',
            line=dict(color='#a855f7', width=3),
            marker=dict(size=8),
            fillcolor='rgba(168, 85, 247, 0.3)'
        ))
        
        fig.update_layout(
            title="Total Detections vs Threshold",
            xaxis_title="Threshold (Strictness)",
            yaxis_title="Duplicate Pairs Detected",
            height=350,
            plot_bgcolor='rgba(15, 15, 35, 0.8)',
            paper_bgcolor='rgba(0, 0, 0, 0)',
            font=dict(color='#e2e8f0')
        )
        
        st.plotly_chart(fig, width='stretch')
        methods = {}
        for d in st.session_state.duplicates:
            method = d.get('method', 'Unknown')
            methods[method] = methods.get(method, 0) + 1
        
        fig = go.Figure(data=[go.Pie(
            labels=list(methods.keys()),
            values=list(methods.values()),
            hole=0.4,
            marker=dict(colors=['#6366f1', '#a855f7', '#ec4899']),
            textinfo='label+percent',
            textfont=dict(color='#e2e8f0')
        )])
        
        fig.update_layout(
            title="Detection Method Breakdown",
            height=350,
            plot_bgcolor='rgba(0, 0, 0, 0)',
            paper_bgcolor='rgba(0, 0, 0, 0)',
            font=dict(color='#e2e8f0')
        )
        
        st.plotly_chart(fig, width='stretch')
    
    # Performance summary
    st.markdown("---")
    st.markdown("### Mirror of Maya Performance Summary")
    
    best_idx = df_cal['f1'].idxmax()
    best_row = df_cal.loc[best_idx]
    
    summary_cols = st.columns(4)
    
    with summary_cols[0]:
        st.metric("Best F1 Score", f"{best_row['f1']:.3f}", 
                 f"at threshold {best_row['threshold']:.2f}")
    
    with summary_cols[1]:
        st.metric("Peak Precision", f"{df_cal['precision'].max():.3f}",
                 f"at threshold {df_cal.loc[df_cal['precision'].idxmax(), 'threshold']:.2f}")
    
    with summary_cols[2]:
        st.metric("Peak Recall", f"{df_cal['recall'].max():.3f}",
                 f"at threshold {df_cal.loc[df_cal['recall'].idxmax(), 'threshold']:.2f}")
    
    with summary_cols[3]:
        st.metric("Total Pairs", f"{len(st.session_state.duplicates):,}",
                 f"at current threshold")
def manager_tab():
    """Duplicate manager with deletion queue"""
    if not st.session_state.duplicates:
        st.info("No duplicates found")
        return
    
    clustering_mode = st.session_state.get('clustering_mode', 'basename')
    clusters = organize_clusters(st.session_state.duplicates, mode=clustering_mode)
    
    st.info(f"{len(clusters)} groups • {sum(len(c['duplicates']) for c in clusters)} duplicate files")
    
    # Actions
    col1, col2, col3 = st.columns(3)
    
    if col1.button("Select All", width='stretch'):
        for c in clusters:
            for d in c['duplicates']:
                st.session_state.deletion_queue.add(d['path'])
        st.rerun()
    
    if col2.button("Clear", width='stretch'):
        st.session_state.deletion_queue.clear()
        st.rerun()
    
    if st.session_state.deletion_queue and col3.button(
        f"Delete ({len(st.session_state.deletion_queue)})",
        type="primary",
        width='stretch'
    ):
        deleted = 0
        progress_bar = st.progress(0)
        total = len(st.session_state.deletion_queue)
        
        for i, f in enumerate(list(st.session_state.deletion_queue)):
            try:
                os.remove(f)
                st.session_state.deletion_queue.discard(f)
                deleted += 1
            except OSError:
                pass
            progress_bar.progress((i + 1) / total)
        
        # Update duplicates
        st.session_state.duplicates = [
            d for d in st.session_state.duplicates 
            if os.path.exists(d['file1']) and os.path.exists(d['file2'])
        ]
        st.session_state.all_duplicates = [
            d for d in st.session_state.all_duplicates 
            if os.path.exists(d['file1']) and os.path.exists(d['file2'])
        ]
        
        st.success(f"✔ Deleted {deleted} files")
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
                    st.image(cluster['original'], width='stretch')
                    st.caption(get_short_path(cluster['original']))
                except (OSError, ValueError, Exception) as e:
                    st.error(f"Load failed: {e}")
            
            with col_dups:
                st.markdown("*Duplicates*")
                dup_cols = st.columns(min(len(cluster['duplicates']), 3))
                
                for idx, dup in enumerate(cluster['duplicates']):
                    c = dup_cols[idx % 3]
                    try:
                        score_pct = dup['score'] * 100
                        badge_class = get_similarity_class(dup['score'])
                        
                        with open(dup['path'], 'rb') as img_file:
                            img_data = base64.b64encode(img_file.read()).decode()
                        
                        if badge_class == 'similarity-high':
                            color = '#10b981'
                            bg_color = 'rgba(16, 185, 129, 0.9)'
                        elif badge_class == 'similarity-medium':
                            color = '#a855f7'
                            bg_color = 'rgba(168, 85, 247, 0.9)'
                        else:
                            color = '#ef4444'
                            bg_color = 'rgba(239, 68, 68, 0.9)'
                        
                        c.markdown(f'''
                        <div style="position: relative; width: 100%;">
                            <img src="data:image/png;base64,{img_data}" style="width: 100%; display: block;">
                            <div style="position: absolute; top: 8px; right: 8px; 
                                        background: {bg_color}; color: white; 
                                        padding: 4px 8px; border-radius: 4px; 
                                        font-size: 11px; font-weight: bold;
                                        font-family: 'Cinzel', serif;
                                        box-shadow: 0 2px 8px rgba(0,0,0,0.3);">
                                {score_pct:.0f}%
                            </div>
                        </div>
                        ''', unsafe_allow_html=True)
                        
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
                    except Exception as e:
                        c.error(f"Error: {e}")
            
            st.markdown("---")
    
    col_prev, col_center, col_next = st.columns([1, 2, 1])
    
    with col_prev:
        if st.session_state.page > 0 and st.button("← Prev", width='stretch'):
            st.session_state.page -= 1
            st.rerun()
    
    with col_center:
        st.markdown(f"<div style='text-align: center; padding-top: 0.5rem; font-family: Inter, sans-serif; color: #94a3b8;'>Page {st.session_state.page + 1} / {total_pages}</div>", unsafe_allow_html=True)
    
    with col_next:
        if end < len(clusters) and st.button("Next →", width='stretch'):
            st.session_state.page += 1
            st.rerun()

def search_tab():
    st.markdown("### Image Search")
    
    col_upload, col_settings = st.columns([2, 1])
    
    with col_upload:
        uploaded = st.file_uploader("Upload image", type=['png', 'jpg', 'jpeg', 'bmp', 'webp'])
    
    with col_settings:
        query_threshold = st.slider("Threshold", 0.30, 0.99, 0.75, 0.01, key="query_thresh")
        max_results = st.number_input("Max Results", 1, 100, 50)
    
    if uploaded and st.session_state.detector:
        query_path = config.TEMP_QUERY_FILE
        with open(query_path, "wb") as f:
            f.write(uploaded.getbuffer())

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(query_path, caption="Query", width='stretch')

        with st.spinner("Searching..."):
            results = st.session_state.detector.find_matches_for_file(
                query_path,
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
                                st.image(res['path'], width='stretch')
                                score_pct = res['score'] * 100
                                badge_class = get_similarity_class(res['score'])
                                st.markdown(
                                    f'<span class="similarity-badge {badge_class}">{score_pct:.0f}%</span>',
                                    unsafe_allow_html=True
                                )
                                st.caption(get_short_path(res['path']))
                            except Exception as e:
                                st.error(f"Load error: {e}")
        else:
            st.warning(f"No matches at {query_threshold:.0%}")
    elif not st.session_state.detector:
        st.info("Run scan to enable search")

def analytics_tab():
    st.markdown("### Analytics")
    
    if not st.session_state.duplicates:
        st.info("Run a scan to view analytics")
        return
    
    clustering_mode = st.session_state.get('clustering_mode', 'basename')
    clusters = organize_clusters(st.session_state.duplicates, mode=clustering_mode)
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
    
    st.dataframe(df_details, width='stretch', height=400)

def hash_duplicates_tab():
    st.markdown("### Hash-Based Duplicate Detection")
    
    if not st.session_state.detector:
        st.info("Run a scan first to enable hash detection")
        return
    
    if hasattr(st.session_state.detector, 'fast_duplicates') and st.session_state.detector.fast_duplicates:
        hash_dups = st.session_state.detector.fast_duplicates
        
        st.success(f"Found {len(hash_dups)} exact/near-exact duplicates via perceptual hashing")
        
        st.markdown("---")
        
        for i in range(0, len(hash_dups), 3):
            cols = st.columns(3)
            for j, col in enumerate(cols):
                if i + j < len(hash_dups):
                    dup = hash_dups[i + j]
                    with col:
                        try:
                            st.markdown(f"**Pair {i + j + 1}**")
                            
                            st.image(dup['file1'], caption="File 1", width='stretch')
                            st.caption(get_short_path(dup['file1']))
                            
                            st.image(dup['file2'], caption="File 2", width='stretch')
                            st.caption(get_short_path(dup['file2']))
                            
                            score_pct = dup['score'] * 100
                            st.markdown(
                                f'<span class="similarity-badge similarity-high">{score_pct:.0f}%</span>',
                                unsafe_allow_html=True
                            )
                            st.caption(f"Method: {dup['method']}")
                            
                            if st.checkbox(f"Delete File 2", key=f"hash_del_{i+j}"):
                                if st.button(f"🗑️ Confirm Delete", key=f"hash_confirm_{i+j}", type="primary"):
                                    try:
                                        os.remove(dup['file2'])
                                        st.success("✔ Deleted")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error: {e}")
                        except Exception as e:
                            st.error(f"Error loading: {e}")
            
            if i + 3 < len(hash_dups):
                st.markdown("---")
    else:
        st.info("No hash-based duplicates found")

def versus_tab():
    st.markdown("### Image Comparison")
    
    if not st.session_state.detector:
        st.info("Run a scan first to enable comparison")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Image 1**")
        img1 = st.file_uploader("Upload first image", type=['png', 'jpg', 'jpeg', 'bmp', 'webp'], key="img1")
    
    with col2:
        st.markdown("**Image 2**")
        img2 = st.file_uploader("Upload second image", type=['png', 'jpg', 'jpeg', 'bmp', 'webp'], key="img2")
    
    if img1 and img2:
        # Save temp files
        temp1 = os.path.join(config.TEMP_DIR, "temp_img1.jpg")
        temp2 = os.path.join(config.TEMP_DIR, "temp_img2.jpg")
        
        with open(temp1, "wb") as f:
            f.write(img1.getbuffer())
        with open(temp2, "wb") as f:
            f.write(img2.getbuffer())
        
        # Display images
        col_disp1, col_disp2 = st.columns(2)
        with col_disp1:
            st.image(temp1, width='stretch')
        with col_disp2:
            st.image(temp2, width='stretch')
        
        st.markdown("---")
        
        # Compare
        with st.spinner("Comparing..."):
            result = st.session_state.detector.compare_two_images(temp1, temp2)
        
        if result:
            similarity_pct = result['similarity'] * 100
            
            # Large similarity display
            st.markdown(f"""
            <div style='text-align: center; padding: 2rem;'>
                <h1 style='font-family: Cinzel, serif; font-size: 4rem; margin: 0;
                           background: linear-gradient(135deg, #6366f1, #a855f7);
                           -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>{similarity_pct:.1f}%</h1>
                <p style='font-family: Inter, sans-serif; font-size: 1.5rem; color: #94a3b8;'>Similarity</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Metrics
            col_m1, col_m2, col_m3 = st.columns(3)
            
            with col_m1:
                st.metric("DINOv2 Similarity", f"{result['similarity']:.4f}")
            
            with col_m2:
                if result['hash_distance'] is not None:
                    st.metric("Hash Distance", result['hash_distance'])
                else:
                    st.metric("Hash Distance", "N/A")
            
            with col_m3:
                match_status = "MATCH" if result['match'] else "NO MATCH"
                st.metric("Status", match_status)
            
            # Interpretation
            st.markdown("---")
            st.markdown("### Interpretation")
            
            if similarity_pct >= 90:
                st.success("**Very Similar** - Likely duplicates or minor variations")
            elif similarity_pct >= 75:
                st.info("**Similar** - Related images with noticeable differences")
            elif similarity_pct >= 60:
                st.warning("**Somewhat Similar** - May share some visual elements")
            else:
                st.error("**Different** - Images are quite different")
            
            if result['hash_distance'] is not None:
                if result['hash_distance'] <= 5:
                    st.success(f"Hash distance: {result['hash_distance']} - Perceptually very similar")
                elif result['hash_distance'] <= 10:
                    st.info(f"Hash distance: {result['hash_distance']} - Perceptually similar")
                else:
                    st.warning(f"Hash distance: {result['hash_distance']} - Perceptually different")
        else:
            st.error("Failed to compare images")


def architecture_tab():
    st.markdown("""
    ### System Architecture

    Mirror of Maya uses a **two-phase detection pipeline** combining classical perceptual hashing
    with deep learning embeddings to achieve both speed and accuracy.

    ---

    #### Phase 1: Perceptual Hashing (dHash)
    - **Algorithm**: Difference Hash (dHash) with 16x16 hash size
    - **Purpose**: Fast-pass filter for exact and near-exact duplicates
    - **How it works**: Converts each image to a grayscale gradient fingerprint, then compares
      fingerprints using Hamming distance (threshold ≤ 2 bits)
    - **Complexity**: O(n) for indexing, O(1) per lookup
    - **Strength**: Catches identical copies, minor crops, and JPEG re-compressions instantly

    #### Phase 2: Deep Semantic Embeddings (DINOv2)
    - **Model**: Meta's DINOv2 (self-supervised Vision Transformer)
    - **Variants**: Small (21M), Base (86M), Large (300M) parameters
    - **How it works**: Each image is projected into a high-dimensional embedding space where
      visually similar images cluster together. Similarity is measured via cosine distance.
    - **Index**: FAISS `IndexFlatIP` for exact inner-product search
    - **Strength**: Detects semantically similar images even under heavy transformations
      (cropping, color shifts, overlays)

    ---

    #### Threshold Calibration
    The system auto-calibrates the optimal similarity threshold using **ground truth pairs**
    from the dataset:
    1. Images in the `original/` folder are treated as ground truth sources
    2. Files with matching basenames in other folders (e.g., `jpeg/`, `crops/`) are treated as known duplicates
    3. F1 score is maximized across thresholds from 0.30 to 0.95
    4. The threshold slider allows real-time exploration of the precision-recall tradeoff

    #### Clustering
    Detected duplicate pairs are organized into clusters using **NetworkX graph components**.
    Each cluster has one "original" (selected by path heuristic or highest connectivity)
    and one or more duplicates.

    ---

    #### Tech Stack
    | Component | Technology |
    |-----------|-----------|
    | Frontend | Streamlit |
    | Vision Model | DINOv2 (HuggingFace Transformers) |
    | Hashing | imagehash (dHash) |
    | Vector Search | FAISS (Facebook AI Similarity Search) |
    | Graph Clustering | NetworkX |
    | Visualization | Plotly |
    | Deep Learning | PyTorch |

    #### Key Design Decisions
    - **Two-phase pipeline**: Hash phase eliminates exact duplicates cheaply before expensive
      embedding computation, reducing DINOv2 calls by ~30-50%
    - **L2-normalized embeddings + Inner Product**: Equivalent to cosine similarity but faster
      with FAISS `IndexFlatIP`
    - **Basename-aware clustering**: Leverages dataset structure for ground truth without
      manual annotation
    - **Real-time threshold tuning**: Users can explore precision vs recall tradeoff without
      re-scanning
    """)

    if st.session_state.detector:
        st.markdown("---")
        st.markdown("#### Current Session Stats")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Images Indexed", st.session_state.detector.index.ntotal)
            st.metric("Hash Duplicates (Phase 1)", len(st.session_state.detector.fast_duplicates))
        with col2:
            st.metric("Embedding Dimension", st.session_state.detector.dimension)
            st.metric("Model", st.session_state.selected_model.split("/")[-1])
        with col3:
            st.metric("Device", st.session_state.detector.device.upper())
            st.metric("Optimal Threshold", f"{st.session_state.optimal_thresh:.2f}")