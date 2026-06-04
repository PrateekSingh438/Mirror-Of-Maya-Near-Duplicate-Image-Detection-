"""Mode-aware tab implementations."""

import io
import zipfile

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from PIL import Image

import artifacts as art
from config import CFG
from dedup import cluster_pairs
from search import compare_two, search_index
from stateless import dedup_batch
from ui.components import badge, short_path


# --------------------------------------------------------------------------- #
# Mode B — Upload & Dedup (always available)
# --------------------------------------------------------------------------- #
def upload_dedup_tab():
    st.markdown("### Upload & Dedup")
    st.caption("Upload a batch of images (or a .zip). They are embedded and "
               "clustered in memory — nothing is stored on the server.")

    col_a, col_b = st.columns(2)
    with col_a:
        files = st.file_uploader("Images", accept_multiple_files=True,
                                 type=[e.strip(".") for e in CFG.SUPPORTED_EXTENSIONS],
                                 key="mb_files")
    with col_b:
        zip_file = st.file_uploader("…or a .zip of images", type=["zip"], key="mb_zip")

    if st.button("Find Duplicates", type="primary"):
        items, raw = _collect_uploads(files, zip_file)
        if len(items) < 2:
            st.warning("Upload at least 2 readable images.")
        else:
            status = st.empty()
            with st.spinner("Working…"):
                result = dedup_batch(items, progress=lambda m: status.write(m))
            status.empty()
            st.session_state.mb_result = result
            st.session_state.mb_images = raw
            st.session_state.mb_remove = set()

    result = st.session_state.mb_result
    if not result:
        st.info("Upload images and click **Find Duplicates**.")
        return

    threshold = st.session_state.threshold
    clusters = cluster_pairs([p for p in result["pairs"] if p["score"] >= threshold],
                             meta=result["meta"], mode="semantic")
    dup_count = sum(len(c["duplicates"]) for c in clusters)

    c1, c2, c3 = st.columns(3)
    c1.metric("Images", f"{result['n_images']:,}")
    c2.metric("Duplicate groups", f"{len(clusters):,}")
    c3.metric("Duplicate images", f"{dup_count:,}")
    st.caption(f"At threshold {threshold:.2f}. Move the sidebar slider to re-cluster instantly.")

    if not clusters:
        st.success("No near-duplicates found at this threshold.")
        return

    st.markdown("---")
    for gi, cluster in enumerate(clusters):
        st.markdown(f"**Group {gi + 1}** · {len(cluster['duplicates'])} duplicate(s)")
        cols = st.columns(min(1 + len(cluster["duplicates"]), 4))
        _render_uploaded(cols[0], cluster["original"], "Original", None)
        for di, dup in enumerate(cluster["duplicates"]):
            col = cols[(di + 1) % len(cols)]
            _render_uploaded(col, dup["id"], None, dup["score"])
        st.markdown("---")

    _download_deduped(clusters)


def _collect_uploads(files, zip_file):
    items, raw = [], {}
    for f in files or []:
        data = f.getvalue()
        img = _open(data)
        if img is not None:
            items.append((f.name, img))
            raw[f.name] = data
    if zip_file is not None:
        with zipfile.ZipFile(io.BytesIO(zip_file.getvalue())) as zf:
            for name in zf.namelist():
                if name.endswith("/") or not name.lower().endswith(CFG.SUPPORTED_EXTENSIONS):
                    continue
                data = zf.read(name)
                img = _open(data)
                if img is not None:
                    items.append((name, img))
                    raw[name] = data
    return items, raw


def _open(data):
    try:
        return Image.open(io.BytesIO(data)).convert("RGB")
    except (OSError, ValueError):
        return None


def _render_uploaded(col, label, title, score):
    data = st.session_state.mb_images.get(label)
    with col:
        if title:
            st.markdown(f"*{title}*")
        if data:
            st.image(data, width="stretch")
        st.caption(short_path(label))
        if score is not None:
            st.markdown(badge(score), unsafe_allow_html=True)
            checked = st.checkbox("mark duplicate", value=label in st.session_state.mb_remove,
                                  key=f"mb_rm_{label}")
            (st.session_state.mb_remove.add if checked
             else st.session_state.mb_remove.discard)(label)


def _download_deduped(clusters):
    default_remove = {d["id"] for c in clusters for d in c["duplicates"]}
    remove = st.session_state.mb_remove or default_remove
    keep = [lbl for lbl in st.session_state.mb_images if lbl not in remove]

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for lbl in keep:
            zf.writestr(lbl, st.session_state.mb_images[lbl])
    st.download_button(
        f"⬇ Download deduped set ({len(keep)} kept, {len(remove)} removed)",
        data=buf.getvalue(), file_name="deduped.zip", mime="application/zip",
        type="primary",
    )


# --------------------------------------------------------------------------- #
# Mode A — Search a prebuilt corpus
# --------------------------------------------------------------------------- #
def search_tab(bundle):
    st.markdown("### Search the Corpus")
    if not bundle:
        st.info("No prebuilt corpus is loaded. Configure an artifact bundle "
                "(see README) or use **Upload & Dedup** instead.")
        return

    meta = bundle["meta"]
    ids = [str(x) for x in meta["id"].tolist()]
    row_by_id = {str(r["id"]): r for _, r in meta.iterrows()}

    uploaded = st.file_uploader("Query image", type=["png", "jpg", "jpeg", "bmp", "webp"])
    top_k = st.number_input("Max results", 1, 100, 24)
    if not uploaded:
        st.caption("Upload an image to find its matches in the corpus.")
        return

    query = Image.open(io.BytesIO(uploaded.getvalue())).convert("RGB")
    st.image(query, caption="Query", width=240)

    with st.spinner("Searching…"):
        results = search_index(bundle["index"], ids, query,
                               threshold=st.session_state.threshold, top_k=int(top_k))
    if not results:
        st.warning(f"No matches at threshold {st.session_state.threshold:.2f}.")
        return

    st.success(f"{len(results)} matches")
    _grid([(r["id"], r["score"]) for r in results], bundle, row_by_id)


# --------------------------------------------------------------------------- #
# Mode A — Browse precomputed clusters
# --------------------------------------------------------------------------- #
def manager_tab(bundle):
    st.markdown("### Corpus Duplicate Clusters")
    if not bundle:
        st.info("No prebuilt corpus is loaded.")
        return

    meta = bundle["meta"]
    row_by_id = {str(r["id"]): r for _, r in meta.iterrows()}
    clustered = meta[meta["cluster_id"] >= 0]
    groups = sorted(clustered.groupby("cluster_id"),
                    key=lambda kv: len(kv[1]), reverse=True)
    if not groups:
        st.success("No duplicate clusters in this corpus.")
        return

    st.info(f"{len(groups)} clusters · {len(clustered)} images")
    per_page = CFG.CLUSTERS_PER_PAGE
    pages = max(1, (len(groups) - 1) // per_page + 1)
    page = st.session_state.manager_page
    start = page * per_page

    for cid, grp in groups[start:start + per_page]:
        rows = grp.sort_values("is_original", ascending=False)
        st.markdown(f"**Cluster {cid}** · {len(rows)} images")
        members = [(str(r["id"]), 1.0 if r["is_original"] else None)
                   for _, r in rows.iterrows()]
        _grid(members, bundle, row_by_id)
        st.markdown("---")

    p1, p2, p3 = st.columns([1, 2, 1])
    if page > 0 and p1.button("← Prev"):
        st.session_state.manager_page -= 1
        st.rerun()
    p2.markdown(f"<div style='text-align:center'>Page {page + 1}/{pages}</div>",
                unsafe_allow_html=True)
    if start + per_page < len(groups) and p3.button("Next →"):
        st.session_state.manager_page += 1
        st.rerun()


def _grid(items, bundle, row_by_id):
    for i in range(0, len(items), 3):
        cols = st.columns(3)
        for col, (img_id, score) in zip(cols, items[i:i + 3]):
            with col:
                tp = art.thumb_path(bundle, img_id)
                if tp:
                    st.image(tp, width="stretch")
                row = row_by_id.get(str(img_id), {})
                st.caption(row.get("rel_path", img_id))
                if score is not None and score < 1.0:
                    st.markdown(badge(score), unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Versus (always available)
# --------------------------------------------------------------------------- #
def versus_tab():
    st.markdown("### Compare Two Images")
    c1, c2 = st.columns(2)
    f1 = c1.file_uploader("Image 1", type=["png", "jpg", "jpeg", "bmp", "webp"], key="vs1")
    f2 = c2.file_uploader("Image 2", type=["png", "jpg", "jpeg", "bmp", "webp"], key="vs2")
    if not (f1 and f2):
        st.caption("Upload two images for a direct similarity comparison.")
        return

    img1 = Image.open(io.BytesIO(f1.getvalue())).convert("RGB")
    img2 = Image.open(io.BytesIO(f2.getvalue())).convert("RGB")
    d1, d2 = st.columns(2)
    d1.image(img1, width="stretch")
    d2.image(img2, width="stretch")

    with st.spinner("Comparing…"):
        res = compare_two(img1, img2, threshold=st.session_state.threshold)
    if not res:
        st.error("Comparison failed.")
        return

    pct = res["similarity"] * 100
    st.markdown(f"<h1 style='text-align:center;font-family:Cinzel,serif;"
                f"color:#a855f7'>{pct:.1f}%</h1>", unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    m1.metric("Cosine similarity", f"{res['similarity']:.4f}")
    m2.metric("dHash distance",
              res["hash_distance"] if res["hash_distance"] is not None else "N/A")
    m3.metric("Verdict", "MATCH" if res["match"] else "NO MATCH")


# --------------------------------------------------------------------------- #
# Analytics / Calibration
# --------------------------------------------------------------------------- #
def analytics_tab(bundle):
    st.markdown("### Calibration & Analytics")
    if bundle and bundle.get("calibration", {}).get("history"):
        calib = bundle["calibration"]
        df = pd.DataFrame(calib["history"])
        c1, c2, c3 = st.columns(3)
        c1.metric("Optimal threshold", f"{calib['optimal_threshold']:.2f}")
        c2.metric("F1", f"{calib['f1']:.3f}")
        c3.metric("GT pairs", f"{calib.get('n_ground_truth_pairs', 0):,}")

        fig = go.Figure()
        for col, color in [("f1", "#6366f1"), ("precision", "#10b981"),
                           ("recall", "#ec4899")]:
            fig.add_trace(go.Scatter(x=df["threshold"], y=df[col], mode="lines+markers",
                                     name=col.title(), line=dict(color=color, width=3)))
        fig.add_vline(x=calib["optimal_threshold"], line_dash="dash",
                      line_color="#a855f7", annotation_text="optimal")
        fig.update_layout(height=420, xaxis_title="Threshold", yaxis_title="Score",
                          paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0"))
        st.plotly_chart(fig, width="stretch")
        st.dataframe(df, width="stretch", height=320)
        return

    result = st.session_state.mb_result
    if result and result["pairs"]:
        st.caption("Stateless session has no ground truth — showing the score "
                   "distribution of detected pairs.")
        scores = [p["score"] for p in result["pairs"]]
        fig = go.Figure(go.Histogram(x=scores, nbinsx=30, marker_color="#a855f7"))
        fig.add_vline(x=st.session_state.threshold, line_dash="dash", line_color="#10b981")
        fig.update_layout(height=380, xaxis_title="Cosine similarity",
                          yaxis_title="Pairs", paper_bgcolor="rgba(0,0,0,0)",
                          font=dict(color="#e2e8f0"))
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("Load a corpus bundle, or run a stateless dedup, to see analytics.")


# --------------------------------------------------------------------------- #
# Architecture
# --------------------------------------------------------------------------- #
def architecture_tab(bundle):
    st.markdown("""
### Architecture

**Two components, one shared core.** `embedder.py` and `hashing.py` are imported
by both the offline indexer and this app, so offline and online produce identical
vectors.

- **Offline indexer (`indexer.py`)** — runs where the dataset (and a GPU) live:
  embeds the corpus, builds a FAISS index, calibrates the F1-optimal threshold
  against ground truth, clusters, and writes a portable `./artifacts` bundle
  (index + thumbnails + calibration + manifest).
- **Serving app (this)** — CPU-only, no dataset on disk. **Mode A** loads a
  prebuilt bundle (fetched from local/HF/URL at boot) for Search and cluster
  browsing. **Mode B** dedups an uploaded batch fully in memory.

**Pipeline:** dHash fast-pass (Hamming ≤ 2) for exact/near-exact pairs →
DINOv2 embeddings (L2-normalized) → FAISS `IndexFlatIP` (inner product = cosine)
→ threshold filter → NetworkX connected-components clustering.
    """)
    if bundle:
        m = bundle["manifest"]
        st.markdown("#### Loaded bundle")
        c1, c2, c3 = st.columns(3)
        c1.metric("Images", f"{m.get('n_images', 0):,}")
        c2.metric("Embedding dim", m.get("embedding_dim", "—"))
        c3.metric("FAISS index", m.get("faiss_type", "—"))
        st.json(m.get("lib_versions", {}))
