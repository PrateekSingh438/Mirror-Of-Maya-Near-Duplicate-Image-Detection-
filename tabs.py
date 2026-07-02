import streamlit as st
import os
import shutil
import uuid
import hashlib

import pandas as pd
import plotly.graph_objects as go
import numpy as np

import config
from utils import (organize_clusters, format_file_size, calculate_wasted_space,
                   per_attack_recall, filter_at_threshold)
from ui_components import get_short_path, get_similarity_class, get_thumbnail


# ----------------------------------------------------------------- helpers

def _get_clusters():
    """Build clusters once per rerun; reuse across tabs."""
    key = (st.session_state.current_slider_val, len(st.session_state.duplicates))
    cached = st.session_state.get('_clusters_cache')
    if cached and cached[0] == key:
        return cached[1]
    clusters = organize_clusters(st.session_state.duplicates)
    st.session_state['_clusters_cache'] = (key, clusters)
    return clusters


def _refresh_pairs():
    detector = st.session_state.detector
    all_dups = detector.find_duplicates(config.SCAN_THRESHOLD_FLOOR)
    st.session_state.all_duplicates = all_dups
    st.session_state.duplicates = filter_at_threshold(
        all_dups, st.session_state.current_slider_val)
    st.session_state.deletion_queue = set()
    _bump_selection_gen()
    st.session_state.page = 0
    st.session_state.pop('_clusters_cache', None)


def _bump_selection_gen():
    """Invalidate every manager checkbox by changing their widget keys.

    Streamlit ignores a checkbox's `value=` once the widget has state under
    its key, so 'Select all' / 'Clear selection' cannot flip the visible
    boxes in place - the stale widget state would immediately write the old
    selection back into the queue. New keys force fresh widgets that read
    their initial value from the queue."""
    st.session_state.selection_gen = st.session_state.get('selection_gen', 0) + 1


def _selection_key(path):
    gen = st.session_state.get('selection_gen', 0)
    return f"del_{gen}_" + hashlib.md5(path.encode()).hexdigest()[:12]


def _trash_dir():
    root = st.session_state.get('active_dataset_path') or config.DATASET_PATH
    if not os.path.isdir(root):
        root = config.TEMP_DIR
    trash = os.path.join(root, config.TRASH_DIR_NAME)
    os.makedirs(trash, exist_ok=True)
    return trash


def _soft_delete(paths):
    """Move files to a trash folder (never permanent deletion) and purge them
    from the index. Returns the number of files moved."""
    trash = _trash_dir()
    moves = []
    for f in paths:
        if not os.path.exists(f):
            continue
        dst = os.path.join(trash, f"{uuid.uuid4().hex[:8]}_{os.path.basename(f)}")
        try:
            shutil.move(f, dst)
            moves.append((f, dst))
        except OSError:
            pass

    payload = None
    if moves and st.session_state.detector:
        payload = st.session_state.detector.remove_files([m[0] for m in moves])
    st.session_state.last_deletion = {'moves': moves, 'payload': payload} if moves else None
    if st.session_state.detector:
        _refresh_pairs()
    return len(moves)


def _undo_delete():
    info = st.session_state.last_deletion
    if not info:
        return 0
    restored = 0
    for src, dst in info['moves']:
        try:
            shutil.move(dst, src)
            restored += 1
        except OSError:
            pass
    if info['payload'] and st.session_state.detector:
        st.session_state.detector.restore_files(info['payload'])
    st.session_state.last_deletion = None
    if st.session_state.detector:
        _refresh_pairs()
    return restored


def _image_card(col, path, score=None):
    with col:
        try:
            st.image(get_thumbnail(path), width='stretch')
            if score is not None:
                badge = get_similarity_class(score)
                st.markdown(
                    f'<span class="similarity-badge {badge}">{score * 100:.0f}%</span>',
                    unsafe_allow_html=True)
            st.caption(get_short_path(path))
        except Exception as e:
            st.error(f"Could not load image: {e}")


# --------------------------------------------------------------- dashboard

def dashboard_tab():
    if not st.session_state.duplicates:
        st.info("No scan results yet. Pick a dataset in the sidebar and click "
                "**Scan for duplicates**. You can use a local folder, upload a "
                "ZIP of images, or paste a Google Drive link.")
        return

    clusters = _get_clusters()
    unique_dups = sum(len(c['duplicates']) for c in clusters)
    waste_mb = calculate_wasted_space(clusters)
    scores = [d['score'] for d in st.session_state.duplicates]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Duplicate files", f"{unique_dups:,}",
                help="Files that appear to be copies of another image")
    col2.metric("Groups", f"{len(clusters):,}",
                help="Each group is one image plus all of its copies")
    col3.metric("Space used by copies", format_file_size(waste_mb * 1024 * 1024))
    col4.metric("Average similarity", f"{np.mean(scores):.1%}" if scores else "N/A")

    st.markdown("---")

    eval_summary = st.session_state.get('eval_summary')
    if eval_summary:
        _render_evaluation(eval_summary, clusters)
    else:
        st.info("This dataset has no ground truth (no known answer key), so "
                "accuracy scores can't be computed. Detection still works. "
                "Browse the results in the Manager tab.")


def _render_evaluation(eval_summary, clusters):
    st.markdown("### Accuracy on this dataset")
    st.markdown(
        "The dataset includes known duplicate pairs, so the system measured "
        "itself against them. The threshold was chosen on half of the image "
        "groups; the scores below come from the **other half**, which the "
        "calibration never saw.")

    holdout = eval_summary['holdout']
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("F1 score (held-out)", f"{holdout['f1']:.1%}",
                help="Balance of precision and recall on unseen groups")
    col2.metric("Precision (held-out)", f"{holdout['precision']:.1%}",
                help="Of the pairs flagged as duplicates, how many really are")
    col3.metric("Recall (held-out)", f"{holdout['recall']:.1%}",
                help="Of the real duplicate pairs, how many were found")
    col4.metric("Chosen threshold", f"{eval_summary['threshold']:.2f}")
    st.caption(f"Ground truth: {eval_summary['n_gt_pairs']:,} duplicate pairs "
               f"across {eval_summary['n_groups']} image groups.")

    df_cal = pd.DataFrame(st.session_state.calibration_history)
    viz_tabs = st.tabs(["Threshold sweep", "Score distribution",
                        "Per-attack recall", "Detection insights"])
    with viz_tabs[0]:
        _render_calibration_curves(df_cal, eval_summary['threshold'])
    with viz_tabs[1]:
        _render_score_distribution()
    with viz_tabs[2]:
        _render_attack_recall(clusters)
    with viz_tabs[3]:
        _render_detection_insights(df_cal)


def _render_calibration_curves(df_cal, chosen_threshold):
    st.markdown("How precision, recall and F1 change as the threshold moves "
                "(measured on the full ground truth).")

    col_chart, col_table = st.columns([2, 1])
    with col_chart:
        fig = go.Figure()
        for name, color in (("f1", "#6366f1"), ("precision", "#10b981"), ("recall", "#ec4899")):
            fig.add_trace(go.Scatter(
                x=df_cal['threshold'], y=df_cal[name],
                mode='lines', name=name.capitalize(),
                line=dict(color=color, width=3),
            ))
        fig.add_vline(x=chosen_threshold, line_dash="dash", line_color="#f59e0b",
                      line_width=2, annotation_text=f"Chosen: {chosen_threshold:.2f}",
                      annotation_position="top")
        fig.update_layout(
            xaxis_title="Threshold", yaxis_title="Score",
            hovermode='x unified', height=420,
            plot_bgcolor='rgba(15, 15, 35, 0.8)', paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e2e8f0', size=12),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig, width='stretch')

    with col_table:
        st.markdown("**Sweep values**")
        st.dataframe(
            df_cal[["threshold", "f1", "precision", "recall"]].style.format({
                'threshold': '{:.2f}', 'f1': '{:.3f}',
                'precision': '{:.3f}', 'recall': '{:.3f}',
            }),
            width='stretch', height=420,
        )


def _render_score_distribution():
    st.markdown("Similarity scores of all detected pairs. Exact copies found "
                "by hashing sit near 1.0.")
    scores = [d['score'] for d in st.session_state.duplicates]
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=scores, nbinsx=30,
        marker=dict(color='#a855f7', line=dict(color='#1e293b', width=1)),
    ))
    fig.add_vline(x=st.session_state.current_slider_val, line_dash="dash",
                  line_color="#10b981", line_width=2,
                  annotation_text="Current threshold")
    fig.update_layout(
        xaxis_title="Similarity score", yaxis_title="Number of pairs", height=400,
        plot_bgcolor='rgba(15, 15, 35, 0.8)', paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e2e8f0'), showlegend=False,
    )
    st.plotly_chart(fig, width='stretch')


def _render_attack_recall(clusters):
    st.markdown("For each kind of modification in the dataset: how many of "
                "those copies were traced back to their source image?")
    dataset_path = st.session_state.get('active_dataset_path') or config.DATASET_PATH
    rows = per_attack_recall(clusters, st.session_state.gt_groups, dataset_path)
    if not rows:
        st.info("No attack folders recognized in this dataset.")
        return

    df = pd.DataFrame(rows)
    fig = go.Figure(go.Bar(
        x=df['recall'], y=df['attack'], orientation='h',
        marker=dict(color='#6366f1'),
        text=[f"{r:.0%}" for r in df['recall']], textposition='auto',
    ))
    fig.update_layout(
        xaxis_title="Recall", yaxis_title="Modification type",
        xaxis=dict(range=[0, 1]), height=max(300, 28 * len(df)),
        plot_bgcolor='rgba(15, 15, 35, 0.8)', paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e2e8f0'),
    )
    st.plotly_chart(fig, width='stretch')
    st.dataframe(
        df.style.format({'recall': '{:.1%}'}),
        width='stretch',
    )


def _render_detection_insights(df_cal):
    col1, col2 = st.columns(2)

    with col1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_cal['threshold'], y=df_cal['count'],
            mode='lines', fill='tozeroy',
            line=dict(color='#a855f7', width=3),
            fillcolor='rgba(168, 85, 247, 0.3)',
        ))
        fig.update_layout(
            title="Pairs detected vs threshold",
            xaxis_title="Threshold", yaxis_title="Detected pairs", height=350,
            plot_bgcolor='rgba(15, 15, 35, 0.8)', paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e2e8f0'),
        )
        st.plotly_chart(fig, width='stretch')

    with col2:
        methods = {}
        for d in st.session_state.duplicates:
            m = d.get('method', 'Unknown')
            methods[m] = methods.get(m, 0) + 1
        fig = go.Figure(data=[go.Pie(
            labels=list(methods.keys()), values=list(methods.values()), hole=0.4,
            marker=dict(colors=['#6366f1', '#a855f7', '#ec4899']),
            textinfo='label+percent', textfont=dict(color='#e2e8f0'),
        )])
        fig.update_layout(
            title="How each pair was found", height=350,
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e2e8f0'),
        )
        st.plotly_chart(fig, width='stretch')


# ----------------------------------------------------------------- manager

def manager_tab():
    if not st.session_state.duplicates:
        st.info("No duplicates to manage yet. Run a scan first.")
        return

    clusters = _get_clusters()
    demo_mode = st.session_state.get('demo_mode', False)

    if demo_mode:
        st.info(f"{len(clusters)} groups • "
                f"{sum(len(c['duplicates']) for c in clusters)} duplicate files. "
                f"This is the built-in demo dataset, so cleanup is disabled. "
                f"Scan your own images to select and remove copies.")
    else:
        st.info(f"{len(clusters)} groups • "
                f"{sum(len(c['duplicates']) for c in clusters)} duplicate files. "
                f"Deleted files are moved to a trash folder, not erased, so you can undo.")

        if st.session_state.get('last_deletion'):
            n = len(st.session_state.last_deletion['moves'])
            if st.button(f"Undo last deletion ({n} files)"):
                restored = _undo_delete()
                st.success(f"Restored {restored} files")
                st.rerun()

        col1, col2, col3 = st.columns(3)
        if col1.button("Select all duplicates", width='stretch'):
            for c in clusters:
                for d in c['duplicates']:
                    st.session_state.deletion_queue.add(d['path'])
            _bump_selection_gen()
            st.rerun()
        if col2.button("Clear selection", width='stretch'):
            st.session_state.deletion_queue.clear()
            _bump_selection_gen()
            st.rerun()

        queue = st.session_state.deletion_queue
        if queue:
            with st.expander(f"Review selection ({len(queue)} files)"):
                for f in sorted(queue):
                    st.caption(get_short_path(f))
            if col3.button(f"Move {len(queue)} files to trash", type="primary",
                           width='stretch'):
                moved = _soft_delete(list(queue))
                st.success(f"Moved {moved} files to trash")
                st.rerun()

    st.markdown("---")

    per_page = config.CLUSTERS_PER_PAGE
    total_pages = max(1, (len(clusters) - 1) // per_page + 1)
    st.session_state.page = min(st.session_state.page, total_pages - 1)
    start = st.session_state.page * per_page
    end = min(start + per_page, len(clusters))

    for i, cluster in enumerate(clusters[start:end]):
        with st.container():
            st.markdown(f"**Group {start + i + 1}**: "
                        f"{len(cluster['duplicates'])} copies")
            col_orig, col_dups = st.columns([1, 3])

            with col_orig:
                st.markdown("*Keep (best version)*")
                _image_card(col_orig, cluster['original'])

            with col_dups:
                st.markdown("*Copies*")
                n_cols = min(len(cluster['duplicates']), 3)
                dup_cols = st.columns(n_cols)
                for idx, dup in enumerate(cluster['duplicates']):
                    c = dup_cols[idx % n_cols]
                    _image_card(c, dup['path'], dup['score'])
                    if demo_mode:
                        continue
                    selected = c.checkbox(
                        "Select for deletion", key=_selection_key(dup['path']),
                        value=dup['path'] in st.session_state.deletion_queue)
                    if selected:
                        st.session_state.deletion_queue.add(dup['path'])
                    else:
                        st.session_state.deletion_queue.discard(dup['path'])
            st.markdown("---")

    col_prev, col_center, col_next = st.columns([1, 2, 1])
    with col_prev:
        if st.session_state.page > 0 and st.button("← Previous", width='stretch'):
            st.session_state.page -= 1
            st.rerun()
    with col_center:
        st.markdown(
            f"<div style='text-align: center; padding-top: 0.5rem; color: #94a3b8;'>"
            f"Page {st.session_state.page + 1} of {total_pages}</div>",
            unsafe_allow_html=True)
    with col_next:
        if end < len(clusters) and st.button("Next →", width='stretch'):
            st.session_state.page += 1
            st.rerun()


# ------------------------------------------------------------------ search

def search_tab():
    st.markdown("### Search by image")
    st.markdown("Upload any image to find its copies and near-copies in the "
                "scanned dataset.")

    if not st.session_state.detector:
        st.info("Run a scan first, then search the indexed images here.")
        return

    col_upload, col_settings = st.columns([2, 1])
    with col_upload:
        uploaded = st.file_uploader("Query image",
                                    type=['png', 'jpg', 'jpeg', 'bmp', 'webp'])
    with col_settings:
        query_threshold = st.slider("Minimum similarity", 0.40, 0.99, 0.75, 0.01,
                                    key="query_thresh")
        max_results = st.number_input("Max results", 1, 100, 50)

    # One-click sample queries (shipped with the repo) so visitors can try
    # the search without having any images of their own.
    samples = []
    if os.path.isdir(config.DEMO_SAMPLES_DIR):
        samples = sorted(
            os.path.join(config.DEMO_SAMPLES_DIR, f)
            for f in os.listdir(config.DEMO_SAMPLES_DIR)
            if f.lower().endswith(config.SUPPORTED_EXTENSIONS)
        )
    if samples and not uploaded:
        st.caption("No image handy? Try one of these:")
        sample_cols = st.columns(len(samples))
        for scol, spath in zip(sample_cols, samples):
            name = os.path.splitext(os.path.basename(spath))[0]
            label = name.split("_", 1)[-1].replace("_", " ").capitalize()
            if scol.button(label, key=f"sample_{name}", width='stretch'):
                st.session_state.sample_query = spath

    if uploaded:
        st.session_state.sample_query = None
        ext = os.path.splitext(uploaded.name)[1] or ".jpg"
        query_path = os.path.join(config.TEMP_DIR,
                                  f"query_{st.session_state.session_uid}{ext}")
        with open(query_path, "wb") as f:
            f.write(uploaded.getbuffer())
    elif st.session_state.get('sample_query') and os.path.exists(st.session_state.sample_query):
        query_path = st.session_state.sample_query
    else:
        return

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image(query_path, caption="Query", width='stretch')

    with st.spinner("Searching..."):
        results = st.session_state.detector.find_matches_for_file(
            query_path, threshold=query_threshold, top_k=int(max_results))

    if results:
        st.success(f"Found {len(results)} matches")
        for i in range(0, len(results), 3):
            cols = st.columns(3)
            for j, col in enumerate(cols):
                if i + j < len(results):
                    res = results[i + j]
                    _image_card(col, res['path'], res['score'])
    else:
        st.warning(f"No matches at {query_threshold:.0%} similarity. "
                   f"Try lowering the slider.")


# --------------------------------------------------------------- analytics

def analytics_tab():
    st.markdown("### Analytics")
    if not st.session_state.duplicates:
        st.info("Run a scan to see analytics.")
        return

    clusters = _get_clusters()
    scores = [d['score'] for d in st.session_state.duplicates]
    unique_duplicates = sum(len(c['duplicates']) for c in clusters)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Duplicate files", unique_duplicates)
        st.metric("Duplicate pairs", len(st.session_state.duplicates))
    with col2:
        st.metric("Mean similarity", f"{np.mean(scores):.3f}" if scores else "N/A")
        st.metric("Median similarity", f"{np.median(scores):.3f}" if scores else "N/A")
    with col3:
        st.metric("Groups", len(clusters))
        avg_size = unique_duplicates / len(clusters) if clusters else 0
        st.metric("Average group size", f"{avg_size:.1f}")

    st.markdown("---")
    st.markdown("### All detected pairs")
    df_details = pd.DataFrame([
        {
            'Kept file': get_short_path(c['original']),
            'Copy': get_short_path(d['path']),
            'Similarity': f"{d['score']:.3f}",
            'Selected': '✓' if d['path'] in st.session_state.deletion_queue else '',
        }
        for c in clusters
        for d in c['duplicates']
    ])
    st.dataframe(df_details, width='stretch', height=400)


# ---------------------------------------------------------- hash duplicates

def hash_duplicates_tab():
    st.markdown("### Exact copies (hash matches)")
    st.markdown("These pairs were caught by perceptual hashing. They are "
                "byte-near-identical copies (same image, possibly re-saved).")

    if not st.session_state.detector:
        st.info("Run a scan first.")
        return

    hash_dups = [d for d in st.session_state.detector.fast_duplicates
                 if os.path.exists(d['file1']) and os.path.exists(d['file2'])]
    if not hash_dups:
        st.info("No exact copies found by hashing.")
        return

    st.success(f"{len(hash_dups)} exact or near-exact copies found")
    st.markdown("---")

    # Paginated: this tab runs on every rerun, and rendering hundreds of
    # pairs at once (735 in the demo corpus) froze the whole app.
    per_page = 12
    total_pages = max(1, (len(hash_dups) - 1) // per_page + 1)
    page = min(st.session_state.get('hash_page', 0), total_pages - 1)
    st.session_state.hash_page = page
    start = page * per_page
    end = min(start + per_page, len(hash_dups))

    for i in range(start, end, 3):
        cols = st.columns(3)
        for j, col in enumerate(cols):
            if i + j < end:
                dup = hash_dups[i + j]
                with col:
                    st.markdown(f"**Pair {i + j + 1}**: "
                                f"hash distance {dup.get('hash_distance', '?')}")
                    _image_card(col, dup['file1'])
                    _image_card(col, dup['file2'])
                    if not st.session_state.get('demo_mode', False):
                        if st.button("Move copy to trash", key=f"hash_del_{i + j}"):
                            moved = _soft_delete([dup['file2']])
                            if moved:
                                st.success("Moved to trash (undo in Manager tab)")
                            st.rerun()
        if i + 3 < end:
            st.markdown("---")

    col_prev, col_center, col_next = st.columns([1, 2, 1])
    with col_prev:
        if page > 0 and st.button("← Previous", key="hash_prev", width='stretch'):
            st.session_state.hash_page -= 1
            st.rerun()
    with col_center:
        st.markdown(
            f"<div style='text-align: center; padding-top: 0.5rem; color: #94a3b8;'>"
            f"Page {page + 1} of {total_pages}</div>",
            unsafe_allow_html=True)
    with col_next:
        if end < len(hash_dups) and st.button("Next →", key="hash_next", width='stretch'):
            st.session_state.hash_page += 1
            st.rerun()


# ------------------------------------------------------------------ versus

def versus_tab():
    st.markdown("### Compare two images")
    st.markdown("Upload any two images to see how similar the system thinks "
                "they are.")

    if not st.session_state.detector:
        st.info("Run a scan first to load the model, then compare images here.")
        return

    col1, col2 = st.columns(2)
    with col1:
        img1 = st.file_uploader("First image",
                                type=['png', 'jpg', 'jpeg', 'bmp', 'webp'], key="img1")
    with col2:
        img2 = st.file_uploader("Second image",
                                type=['png', 'jpg', 'jpeg', 'bmp', 'webp'], key="img2")

    if not (img1 and img2):
        return

    uid = st.session_state.session_uid
    temp1 = os.path.join(config.TEMP_DIR, f"vs1_{uid}{os.path.splitext(img1.name)[1] or '.jpg'}")
    temp2 = os.path.join(config.TEMP_DIR, f"vs2_{uid}{os.path.splitext(img2.name)[1] or '.jpg'}")
    with open(temp1, "wb") as f:
        f.write(img1.getbuffer())
    with open(temp2, "wb") as f:
        f.write(img2.getbuffer())

    col_disp1, col_disp2 = st.columns(2)
    with col_disp1:
        st.image(temp1, width='stretch')
    with col_disp2:
        st.image(temp2, width='stretch')
    st.markdown("---")

    with st.spinner("Comparing..."):
        result = st.session_state.detector.compare_two_images(
            temp1, temp2, threshold=st.session_state.current_slider_val)

    if not result:
        st.error("Could not read one of the images.")
        return

    similarity_pct = result['similarity'] * 100
    st.markdown(f"""
    <div style='text-align: center; padding: 1.5rem;'>
        <h1 style='font-size: 3.5rem; margin: 0;
                   background: linear-gradient(135deg, #6366f1, #a855f7);
                   -webkit-background-clip: text;
                   -webkit-text-fill-color: transparent;'>{similarity_pct:.1f}%</h1>
        <p style='font-size: 1.2rem; color: #94a3b8;'>similarity</p>
    </div>
    """, unsafe_allow_html=True)

    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Embedding similarity", f"{result['similarity']:.4f}",
                  help="Cosine similarity of the DINOv2 embeddings (1.0 = identical)")
    if result['hash_distance'] is not None:
        col_m2.metric("Hash distance", result['hash_distance'],
                      help="Number of differing bits between the two perceptual "
                           "hashes (0 = identical, under 3 = exact copy)")
    else:
        col_m2.metric("Hash distance", "N/A")
    col_m3.metric("Verdict", "Duplicate" if result['match'] else "Not a duplicate",
                  help=f"Compared against the current threshold "
                       f"({st.session_state.current_slider_val:.2f})")

    st.markdown("---")
    if similarity_pct >= 90:
        st.success("**Very similar**: almost certainly the same image, possibly "
                   "compressed, cropped or recolored.")
    elif similarity_pct >= 75:
        st.info("**Similar**: likely related images with visible differences.")
    elif similarity_pct >= 60:
        st.warning("**Somewhat similar**: they may share content or composition.")
    else:
        st.error("**Different**: these look like different images.")


# ------------------------------------------------------------- architecture

def architecture_tab():
    st.markdown("""
    ### How it works

    The system runs two detection stages and an optional evaluation stage.

    ---

    #### Stage 1: Exact copies (perceptual hashing)
    Every image is reduced to a 256-bit **dHash** fingerprint (a 16x16 map of
    brightness gradients). Two images whose fingerprints differ by at most
    2 bits are exact or near-exact copies, for example the same photo saved
    at a different JPEG quality. All fingerprints are compared against all
    others directly (no shortcuts), so nothing is missed at this stage.

    #### Stage 2: Visual similarity (DINOv2 + FAISS)
    Every image, including the exact copies from Stage 1, is passed through
    **DINOv2**, a vision transformer from Meta AI, producing one normalized
    embedding vector per image (the CLS token). Images are processed in
    batches for speed. A **FAISS range search** then returns *every* pair of
    images whose cosine similarity exceeds the threshold floor. There is no
    top-k cutoff, so large duplicate groups are found completely.

    #### Grouping
    Detected pairs form a graph; connected components become duplicate
    groups. The file kept as "best version" is chosen by image quality
    (resolution, then file size). Filenames are never used for detection.

    ---

    #### Evaluation (only on benchmark datasets)
    If the dataset has a known answer key, meaning copies share filenames
    across folders (like the INRIA copydays benchmark) or carry `_aug_*`
    suffixes, the system builds ground-truth pairs from it and measures itself:

    1. Image groups are split 50/50 into a calibration half and a held-out half.
    2. The similarity threshold is swept from 0.40 to 0.99 in steps of 0.01;
       the F1-optimal value is chosen **on the calibration half only**.
    3. Precision, recall and F1 are then reported **on the held-out half**,
       which the calibration never saw.

    Pairs are compared by full file path. Filenames are used only to build
    the answer key, never by the detector itself, which is why scanning any
    ordinary folder of photos works the same way (just without the scores).

    ---

    #### Technology
    | Component | Library |
    |-----------|---------|
    | Embeddings | DINOv2 via HuggingFace Transformers (PyTorch) |
    | Vector search | FAISS (range search on a flat inner-product index) |
    | Exact-copy hashing | imagehash (dHash) |
    | Grouping | NetworkX connected components |
    | Interface | Streamlit + Plotly |
    """)

    if st.session_state.detector:
        st.markdown("---")
        st.markdown("#### Current session")
        det = st.session_state.detector
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Images indexed", det.index.ntotal)
            st.metric("Exact copies (Stage 1)", len(det.fast_duplicates))
        with col2:
            st.metric("Embedding dimension", det.dimension)
            st.metric("Model", det.model_id.split("/")[-1])
        with col3:
            st.metric("Device", det.device.upper())
            st.metric("Threshold", f"{det.optimal_threshold:.2f}")
        if det.failed_files:
            st.caption(f"{len(det.failed_files)} files could not be read and "
                       f"were skipped.")
