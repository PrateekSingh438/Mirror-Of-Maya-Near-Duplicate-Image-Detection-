import streamlit as st
import os
import hashlib
from datetime import datetime

from PIL import Image

import config
import engine
from engine import DuplicateDetector
from utils import get_dir_size, generate_ground_truth, norm_path
from session_manager import save_session_state, recalculate_metrics


@st.cache_resource(show_spinner=False)
def _load_backbone(model_id):
    return engine.load_backbone(model_id)


def filter_at_threshold(all_duplicates, threshold):
    """Hash-confirmed pairs are exact copies; the cosine slider never hides them."""
    return [d for d in all_duplicates
            if d.get('method') == 'dHash' or d['score'] >= threshold]


def apply_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700;900&family=Inter:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');

        .main {
            background: #0a0a1a;
            background-image:
                radial-gradient(at 20% 30%, rgba(139, 92, 246, 0.15) 0px, transparent 50%),
                radial-gradient(at 80% 0%, rgba(168, 85, 247, 0.12) 0px, transparent 50%),
                radial-gradient(at 60% 100%, rgba(236, 72, 153, 0.12) 0px, transparent 50%);
            color: #e2e8f0;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1a1a3e 0%, #0f0f2e 100%);
            border-right: 2px solid rgba(139, 92, 246, 0.3);
        }

        .main-header {
            font-family: 'Cinzel', serif;
            font-size: 3.5rem;
            font-weight: 900;
            text-align: center;
            background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
            letter-spacing: 0.1em;
        }

        .subtitle {
            font-family: 'Inter', sans-serif;
            font-size: 1.1rem;
            text-align: center;
            color: #a78bfa;
            margin-bottom: 2rem;
            letter-spacing: 0.08em;
        }

        .similarity-badge {
            display: inline-flex;
            align-items: center;
            padding: 0.4rem 0.9rem;
            border-radius: 50px;
            font-weight: 700;
            font-size: 0.875rem;
            font-family: 'Inter', sans-serif;
        }
        .similarity-high {
            background: rgba(16, 185, 129, 0.2);
            color: #10b981;
            border: 2px solid #10b981;
        }
        .similarity-medium {
            background: rgba(168, 85, 247, 0.2);
            color: #a855f7;
            border: 2px solid #a855f7;
        }
        .similarity-low {
            background: rgba(239, 68, 68, 0.2);
            color: #ef4444;
            border: 2px solid #ef4444;
        }

        .stButton > button {
            background: linear-gradient(135deg, #6366f1, #a855f7);
            border: 2px solid rgba(168, 85, 247, 0.5);
            color: white;
            font-family: 'Inter', sans-serif;
            font-weight: 600;
            border-radius: 10px;
        }

        [data-testid="stMetricValue"] {
            font-family: 'Space Grotesk', sans-serif;
            font-weight: 700;
            color: #c4b5fd;
        }

        .stTabs [data-baseweb="tab"] {
            font-family: 'Inter', sans-serif;
            font-weight: 600;
            color: #94a3b8;
        }
        .stTabs [aria-selected="true"] {
            color: #a855f7;
        }
    </style>
    """, unsafe_allow_html=True)


def render_header():
    st.markdown('''
    <div style="text-align: center; margin-bottom: 1.5rem;">
        <h1 class="main-header">MIRROR OF MAYA</h1>
        <p class="subtitle">Near-Duplicate Image Detection</p>
        <div style="color: #64748b; font-size: 0.9rem; max-width: 760px; margin: 0 auto; line-height: 1.6;">
            Finds copies of the same picture even after compression, cropping, resizing
            or color edits, using perceptual hashing for exact copies and DINOv2
            vision-transformer embeddings for everything else.
        </div>
    </div>
    ''', unsafe_allow_html=True)


def render_sidebar():
    with st.sidebar:
        st.markdown("### Controls")
        st.markdown("---")
        _render_model_selection()
        _render_dataset_config()
        st.markdown("---")
        _render_scan_button()
        _render_session_info()


def _render_model_selection():
    with st.expander("Model", expanded=True):
        available_models = {
            "DINOv2 Small (fastest)": "facebook/dinov2-small",
            "DINOv2 Base (balanced)": "facebook/dinov2-base",
            "DINOv2 Large (most accurate, slow)": "facebook/dinov2-large",
        }
        values = list(available_models.values())
        current = st.session_state.selected_model
        index = values.index(current) if current in values else 0
        selected_name = st.selectbox("Embedding model:", list(available_models.keys()), index=index)
        new_model = available_models[selected_name]
        if new_model != st.session_state.selected_model:
            st.session_state.selected_model = new_model
            if st.session_state.detector is not None:
                st.info("Model changed. Run a new scan to apply it.")


def _is_running_locally():
    """True when the app runs on this machine (local paths make sense)."""
    try:
        host = st.context.headers.get("Host", "")
        return "localhost" in host or "127.0.0.1" in host
    except Exception:
        return os.path.exists(config.DATASET_PATH)


def _safe_extract_zip(zip_file, target_dir):
    """Extract a ZIP, refusing entries that try to escape the target folder."""
    import zipfile
    root = os.path.realpath(target_dir)
    with zipfile.ZipFile(zip_file, 'r') as zf:
        for member in zf.infolist():
            dest = os.path.realpath(os.path.join(target_dir, member.filename))
            if not (dest == root or dest.startswith(root + os.sep)):
                raise ValueError(f"Unsafe path inside ZIP: {member.filename}")
        zf.extractall(target_dir)


def _download_from_gdrive(url):
    """Download a ZIP from a Google Drive share link and extract it."""
    import gdown
    import shutil
    import re

    file_id = None
    for pattern in (r'/file/d/([a-zA-Z0-9_-]+)', r'id=([a-zA-Z0-9_-]+)', r'/folders/([a-zA-Z0-9_-]+)'):
        match = re.search(pattern, url)
        if match:
            file_id = match.group(1)
            break
    if not file_id:
        raise ValueError("Could not read a file ID from that link. Use a share link like "
                         "https://drive.google.com/file/d/FILE_ID/view?usp=sharing")

    download_dir = os.path.join(config.TEMP_DIR, "gdrive_dataset")
    if os.path.exists(download_dir):
        shutil.rmtree(download_dir)
    os.makedirs(download_dir, exist_ok=True)

    zip_path = os.path.join(config.TEMP_DIR, "gdrive_download.zip")
    gdown.download(id=file_id, output=zip_path, quiet=False)
    if not os.path.exists(zip_path):
        raise FileNotFoundError("Download failed. Make sure the file is shared as "
                                "'Anyone with the link'.")

    _safe_extract_zip(zip_path, download_dir)
    os.remove(zip_path)
    return download_dir


def _render_dataset_config():
    with st.expander("Dataset", expanded=True):
        is_local = _is_running_locally()
        options = (["Local folder", "Upload ZIP", "Google Drive link"]
                   if is_local else ["Upload ZIP", "Google Drive link"])
        source = st.radio("Where are your images?", options,
                          key="dataset_source_mode", horizontal=True)

        if source == "Local folder":
            dataset_path = st.text_input(
                "Folder path:",
                value=st.session_state.get("active_dataset_path") or config.DATASET_PATH,
                key="local_dataset_path",
                help="Path to a folder of images on this machine. Subfolders are included."
            )
            st.session_state["active_dataset_path"] = dataset_path
            if os.path.isdir(dataset_path):
                st.success(f"Found {get_dir_size(dataset_path):.1f} MB of images")
            else:
                st.info("Enter a valid folder path")

        elif source == "Upload ZIP":
            uploaded_zip = st.file_uploader(
                "Upload a ZIP of images",
                type=["zip"],
                key="dataset_zip_upload",
                help="Any folder structure works. If copies share filenames across folders "
                     "(like the copydays benchmark), accuracy scores are computed too."
            )
            if uploaded_zip is not None:
                import shutil
                upload_dir = os.path.join(config.TEMP_DIR,
                                          f"uploaded_{st.session_state.session_uid}")
                if os.path.exists(upload_dir):
                    shutil.rmtree(upload_dir)
                os.makedirs(upload_dir, exist_ok=True)
                try:
                    _safe_extract_zip(uploaded_zip, upload_dir)
                    st.session_state["active_dataset_path"] = upload_dir
                    st.success(f"Extracted {get_dir_size(upload_dir):.1f} MB")
                except ValueError as e:
                    st.error(str(e))
            else:
                st.info("Upload a ZIP file containing your images")

        elif source == "Google Drive link":
            gdrive_url = st.text_input(
                "Google Drive link:",
                placeholder="https://drive.google.com/file/d/.../view?usp=sharing",
                key="gdrive_url_input",
                help="Link to a ZIP file shared as 'Anyone with the link'."
            )
            if st.button("Download from Drive", key="gdrive_download_btn"):
                if not gdrive_url:
                    st.error("Paste a Google Drive link first")
                else:
                    try:
                        with st.spinner("Downloading from Google Drive..."):
                            download_dir = _download_from_gdrive(gdrive_url)
                        st.session_state["active_dataset_path"] = download_dir
                        st.success(f"Downloaded {get_dir_size(download_dir):.1f} MB")
                    except Exception as e:
                        st.error(f"Download failed: {e}")

        active = st.session_state.get("active_dataset_path")
        if active and os.path.isdir(active):
            st.caption(f"Active dataset: `{active}`")


def _render_scan_button():
    if st.button("Scan for duplicates", type="primary", width='stretch'):
        dataset_path = st.session_state.get('active_dataset_path') or config.DATASET_PATH
        if not dataset_path or not os.path.isdir(dataset_path):
            st.error("No dataset found. Pick a folder, upload a ZIP, or use a Drive link.")
            return
        _run_scan(dataset_path)


def _run_scan(dataset_path):
    start_time = datetime.now()
    model_id = st.session_state.selected_model

    with st.spinner(f"Loading model ({model_id.split('/')[-1]})..."):
        backbone = _load_backbone(model_id)
        detector = DuplicateDetector(model_id, backbone=backbone)

    progress = st.progress(0.0, text="Starting scan...")
    last_pct = [-1]

    def progress_cb(stage, done, total):
        pct = int(100 * done / max(total, 1))
        if pct != last_pct[0]:
            last_pct[0] = pct
            progress.progress(pct / 100, text=f"{stage}: {done:,} / {total:,}")

    detector.bulk_index(dataset_path, progress_cb=progress_cb)
    progress.empty()

    if detector.index.ntotal == 0:
        st.error("No readable images found in that dataset.")
        return

    # Ground truth exists only for benchmark-style datasets. Detection works
    # either way; accuracy scores are simply hidden when there is none.
    gt_groups, gt_pairs = generate_ground_truth(dataset_path)
    eval_summary = None
    if gt_pairs:
        with st.spinner("Calibrating threshold on ground truth..."):
            eval_summary = detector.calibrate_threshold(gt_groups, gt_pairs)

    thresh = eval_summary["threshold"] if eval_summary else config.DEFAULT_THRESHOLD
    detector.optimal_threshold = thresh

    all_dups = detector.find_duplicates(config.SCAN_THRESHOLD_FLOOR)

    st.session_state.detector = detector
    st.session_state.active_dataset_path = dataset_path
    st.session_state.gt_groups = gt_groups
    st.session_state.gt_pairs = gt_pairs
    st.session_state.eval_summary = eval_summary
    st.session_state.calibration_history = eval_summary["history"] if eval_summary else []
    st.session_state.optimal_thresh = thresh
    st.session_state.current_slider_val = thresh
    st.session_state.all_duplicates = all_dups
    st.session_state.duplicates = filter_at_threshold(all_dups, thresh)
    st.session_state.deletion_queue = set()
    st.session_state.last_deletion = None
    st.session_state.page = 0

    scan_time = (datetime.now() - start_time).total_seconds()
    st.session_state.scan_stats = {
        'total_images': detector.index.ntotal,
        'failed_images': len(detector.failed_files),
        'scan_time': scan_time,
        'duplicates_found': len(st.session_state.duplicates),
        'timestamp': datetime.now().isoformat(),
    }

    save_session_state()
    if eval_summary:
        st.success(f"Scan complete. Held-out F1: {eval_summary['holdout']['f1']:.1%} "
                   f"at threshold {thresh:.2f}")
    else:
        st.success("Scan complete. No ground truth in this dataset, so accuracy "
                   "scores are not shown. Detection results are in the tabs below.")
    st.rerun()


def _render_session_info():
    st.markdown("---")
    st.markdown("### Last scan")
    if st.session_state.get('scan_stats'):
        stats = st.session_state.scan_stats
        st.metric("Images indexed", f"{stats['total_images']:,}")
        st.metric("Scan time", f"{stats['scan_time']:.1f}s")
        st.metric("Duplicate pairs", f"{stats['duplicates_found']:,}")
        if stats.get('failed_images'):
            st.caption(f"{stats['failed_images']} files could not be read")
        if 'timestamp' in stats:
            ts = datetime.fromisoformat(stats['timestamp'])
            st.caption(f"Scanned: {ts.strftime('%Y-%m-%d %H:%M')}")
    else:
        st.info("No scan yet")


def render_threshold_control():
    st.markdown("### Similarity threshold")
    st.markdown("How similar two images must be (0 to 1) to count as duplicates. "
                "Higher = stricter.")

    col_slider, col_metrics = st.columns([2, 2])

    with col_slider:
        new_thresh = st.slider(
            "Threshold:",
            min_value=config.MIN_THRESHOLD,
            max_value=config.MAX_THRESHOLD,
            value=st.session_state.current_slider_val,
            step=0.01,
            key="dynamic_threshold",
            help="Higher catches fewer false matches; lower catches more real "
                 "duplicates but risks false matches. Exact copies found by "
                 "hashing are always kept."
        )
        if new_thresh != st.session_state.current_slider_val:
            st.session_state.current_slider_val = new_thresh
            st.session_state.duplicates = filter_at_threshold(
                st.session_state.all_duplicates, new_thresh)
            st.session_state.page = 0

    with col_metrics:
        metrics = recalculate_metrics(st.session_state.current_slider_val)
        if metrics:
            mcol1, mcol2, mcol3 = st.columns(3)
            mcol1.metric("F1", f"{metrics['f1']:.1%}")
            mcol2.metric("Precision", f"{metrics['precision']:.1%}")
            mcol3.metric("Recall", f"{metrics['recall']:.1%}")
        else:
            st.caption("No ground truth in this dataset, so precision/recall "
                       "can't be measured. The pair list below is still live.")

    st.markdown("---")


def get_thumbnail(path):
    """Small cached JPEG for display; falls back to the original file."""
    try:
        stat = os.stat(path)
        key = hashlib.md5(
            f"{norm_path(path)}|{stat.st_mtime_ns}|{stat.st_size}".encode()
        ).hexdigest()
        thumb = os.path.join(config.THUMBS_DIR, key + ".jpg")
        if not os.path.exists(thumb):
            with Image.open(path) as img:
                img = img.convert("RGB")
                img.thumbnail((config.THUMBNAIL_MAX_SIZE, config.THUMBNAIL_MAX_SIZE))
                img.save(thumb, quality=85)
        return thumb
    except Exception:
        return path


def get_short_path(path):
    try:
        if not path:
            return ""
        parent = os.path.basename(os.path.dirname(path))
        filename = os.path.basename(path)
        return f"{parent}/{filename}"
    except (TypeError, ValueError, OSError):
        return os.path.basename(path) if path else ""


def get_similarity_class(score):
    if score >= 0.95:
        return "similarity-high"
    elif score >= 0.88:
        return "similarity-medium"
    return "similarity-low"
