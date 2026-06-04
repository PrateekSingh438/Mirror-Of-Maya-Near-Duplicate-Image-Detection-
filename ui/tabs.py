"""App tabs with plain-language copy (logic unchanged)."""

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
# Find Duplicates (works for everyone — your own images, nothing is stored)
# --------------------------------------------------------------------------- #
def upload_dedup_tab():
    st.subheader("Find duplicates in your own images")
    st.write("Upload a set of pictures (or a ZIP). The app groups together images "
             "that are the same or nearly the same, so you can see and remove the "
             "extra copies. Your images are processed in memory and **never stored**.")

    col_a, col_b = st.columns(2)
    with col_a:
        files = st.file_uploader("Upload images", accept_multiple_files=True,
                                 type=[e.strip(".") for e in CFG.SUPPORTED_EXTENSIONS],
                                 key="mb_files")
    with col_b:
        zip_file = st.file_uploader("…or upload a ZIP of images", type=["zip"], key="mb_zip")

    if st.button("Find duplicates", type="primary"):
        items, raw = _collect_uploads(files, zip_file)
        if len(items) < 2:
            st.warning("Please upload at least 2 images.")
        else:
            status = st.empty()
            with st.spinner("Looking for duplicates…"):
                result = dedup_batch(items, progress=lambda m: status.write(m))
            status.empty()
            st.session_state.mb_result = result
            st.session_state.mb_images = raw
            st.session_state.mb_remove = set()

    result = st.session_state.mb_result
    if not result:
        st.info("Upload some images above, then click **Find duplicates**.")
        return

    threshold = st.session_state.threshold
    clusters = cluster_pairs([p for p in result["pairs"] if p["score"] >= threshold],
                             meta=result["meta"], mode="semantic")
    dup_count = sum(len(c["duplicates"]) for c in clusters)

    c1, c2, c3 = st.columns(3)
    c1.metric("Images checked", f"{result['n_images']:,}")
    c2.metric("Duplicate groups", f"{len(clusters):,}")
    c3.metric("Extra copies found", f"{dup_count:,}")
    st.caption("Tip: drag the **Match strictness** slider in the sidebar to find "
               "more look-alikes or only near-identical images.")

    if not clusters:
        st.success("No duplicates found at this strictness. Try lowering it in the sidebar.")
        return

    st.divider()
    st.write("Each group below shows one image to **keep** and its likely duplicates. "
             "Tick the copies you want to remove, then download the cleaned set.")
    for gi, cluster in enumerate(clusters):
        st.markdown(f"**Group {gi + 1}** — {len(cluster['duplicates'])} possible duplicate(s)")
        cols = st.columns(min(1 + len(cluster["duplicates"]), 4))
        _render_uploaded(cols[0], cluster["original"], "Keep this one", None)
        for di, dup in enumerate(cluster["duplicates"]):
            col = cols[(di + 1) % len(cols)]
            _render_uploaded(col, dup["id"], None, dup["score"])
        st.divider()

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
            st.caption(f"✅ {title}")
        if data:
            st.image(data, width="stretch")
        st.caption(short_path(label))
        if score is not None:
            st.markdown(badge(score), unsafe_allow_html=True)
            checked = st.checkbox("Remove this copy",
                                  value=label in st.session_state.mb_remove,
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
        f"⬇ Download cleaned set ({len(keep)} kept, {len(remove)} removed)",
        data=buf.getvalue(), file_name="cleaned_images.zip", mime="application/zip",
        type="primary",
    )


# --------------------------------------------------------------------------- #
# Search by image (uses the sample library)
# --------------------------------------------------------------------------- #
def search_tab(bundle):
    st.subheader("Search by image")
    if not bundle:
        st.info("This searches a built-in sample image library, which isn't loaded "
                "right now. You can still compare your own images in the "
                "**Find Duplicates** and **Compare Two** tabs.")
        return

    st.write("Upload a picture to find similar images in the sample library.")
    meta = bundle["meta"]
    ids = [str(x) for x in meta["id"].tolist()]
    row_by_id = {str(r["id"]): r for _, r in meta.iterrows()}

    uploaded = st.file_uploader("Upload a picture", type=["png", "jpg", "jpeg", "bmp", "webp"])
    top_k = st.slider("How many results to show", 3, 60, 24)
    if not uploaded:
        return

    query = Image.open(io.BytesIO(uploaded.getvalue())).convert("RGB")
    st.image(query, caption="Your image", width=220)

    with st.spinner("Searching…"):
        results = search_index(bundle["index"], ids, query,
                               threshold=st.session_state.threshold, top_k=int(top_k))
    if not results:
        st.warning("No similar images found. Try lowering **Match strictness** in the sidebar.")
        return

    st.success(f"Found {len(results)} similar image(s).")
    _grid([(r["id"], r["score"]) for r in results], bundle, row_by_id)


# --------------------------------------------------------------------------- #
# Duplicate groups already found in the sample library
# --------------------------------------------------------------------------- #
def manager_tab(bundle):
    st.subheader("Duplicate groups in the sample library")
    if not bundle:
        st.info("The sample image library isn't loaded right now.")
        return

    meta = bundle["meta"]
    row_by_id = {str(r["id"]): r for _, r in meta.iterrows()}
    clustered = meta[meta["cluster_id"] >= 0]
    groups = sorted(clustered.groupby("cluster_id"),
                    key=lambda kv: len(kv[1]), reverse=True)
    if not groups:
        st.success("No duplicate groups were found in this library.")
        return

    st.write(f"The app already grouped **{len(clustered):,}** library images into "
             f"**{len(groups):,}** sets of look-alikes. Browse them below.")
    per_page = CFG.CLUSTERS_PER_PAGE
    pages = max(1, (len(groups) - 1) // per_page + 1)
    page = st.session_state.manager_page
    start = page * per_page

    for cid, grp in groups[start:start + per_page]:
        rows = grp.sort_values("is_original", ascending=False)
        st.markdown(f"**Group {cid}** — {len(rows)} similar images")
        members = [(str(r["id"]), 1.0 if r["is_original"] else None)
                   for _, r in rows.iterrows()]
        _grid(members, bundle, row_by_id)
        st.divider()

    p1, p2, p3 = st.columns([1, 2, 1])
    if page > 0 and p1.button("← Previous"):
        st.session_state.manager_page -= 1
        st.rerun()
    p2.markdown(f"<div style='text-align:center'>Page {page + 1} of {pages}</div>",
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
# Compare two images
# --------------------------------------------------------------------------- #
def versus_tab():
    st.subheader("Compare two images")
    st.write("Upload any two pictures to see how similar they are.")
    c1, c2 = st.columns(2)
    f1 = c1.file_uploader("First image", type=["png", "jpg", "jpeg", "bmp", "webp"], key="vs1")
    f2 = c2.file_uploader("Second image", type=["png", "jpg", "jpeg", "bmp", "webp"], key="vs2")
    if not (f1 and f2):
        return

    img1 = Image.open(io.BytesIO(f1.getvalue())).convert("RGB")
    img2 = Image.open(io.BytesIO(f2.getvalue())).convert("RGB")
    d1, d2 = st.columns(2)
    d1.image(img1, width="stretch")
    d2.image(img2, width="stretch")

    with st.spinner("Comparing…"):
        res = compare_two(img1, img2, threshold=st.session_state.threshold)
    if not res:
        st.error("Sorry, those images couldn't be compared.")
        return

    pct = res["similarity"] * 100
    verdict = ("These look like the same image" if pct >= 90 else
               "These are quite similar" if pct >= 75 else
               "These share some features" if pct >= 55 else
               "These look different")
    st.markdown(f"<h2 style='text-align:center;color:#c4b5fd'>{pct:.0f}% similar</h2>"
                f"<p style='text-align:center;color:#aab2c5'>{verdict}</p>",
                unsafe_allow_html=True)
    m1, m2 = st.columns(2)
    m1.metric("Similarity", f"{pct:.0f}%", help="How alike the two images look to the AI model.")
    m2.metric("Match?", "Yes" if res["match"] else "No",
              help="Whether they pass your current match-strictness setting.")


# --------------------------------------------------------------------------- #
# Accuracy (the calibration / PR curve, explained plainly)
# --------------------------------------------------------------------------- #
def analytics_tab(bundle):
    st.subheader("How accurate is it?")
    if bundle and bundle.get("calibration", {}).get("history"):
        calib = bundle["calibration"]
        st.write("There's a trade-off when matching images. Make it **stricter** and "
                 "almost every flagged match is a true duplicate, but you miss some. "
                 "Make it **looser** and you catch nearly all duplicates, but a few "
                 "wrong matches slip in. This chart shows that trade-off, measured on "
                 f"a benchmark of **{calib.get('n_ground_truth_pairs', 0):,}** known pairs.")

        c1, c2, c3 = st.columns(3)
        c1.metric("Best balance at strictness", f"{calib['optimal_threshold']:.2f}")
        c2.metric("Catches (recall)", f"{calib['recall'] * 100:.0f}%",
                  help="Of all real duplicates, how many it finds at the best setting.")
        c3.metric("Correct matches (precision)", f"{calib['precision'] * 100:.0f}%",
                  help="Of everything it flags, how many are truly duplicates.")

        df = pd.DataFrame(calib["history"])
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["threshold"], y=df["recall"] * 100,
                                 mode="lines+markers", name="Catches duplicates (%)",
                                 line=dict(color="#ec4899", width=3)))
        fig.add_trace(go.Scatter(x=df["threshold"], y=df["precision"] * 100,
                                 mode="lines+markers", name="Matches are correct (%)",
                                 line=dict(color="#34d399", width=3)))
        fig.add_vline(x=calib["optimal_threshold"], line_dash="dash",
                      line_color="#c084fc", annotation_text="best balance")
        fig.update_layout(height=420, xaxis_title="Match strictness",
                          yaxis_title="Percent", paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(255,255,255,0.03)",
                          font=dict(color="#e6e9f2"),
                          legend=dict(orientation="h", y=1.12))
        st.plotly_chart(fig, width="stretch")
        return

    result = st.session_state.mb_result
    if result and result["pairs"]:
        st.write("This shows how confident the app was about the matches it found in "
                 "your uploaded images. The line marks your current strictness setting.")
        scores = [p["score"] * 100 for p in result["pairs"]]
        fig = go.Figure(go.Histogram(x=scores, nbinsx=30, marker_color="#a855f7"))
        fig.add_vline(x=st.session_state.threshold * 100, line_dash="dash", line_color="#34d399")
        fig.update_layout(height=380, xaxis_title="Similarity of matched pairs (%)",
                          yaxis_title="Number of pairs", paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(255,255,255,0.03)", font=dict(color="#e6e9f2"))
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("Run **Find Duplicates** on some images, or load the sample library, "
                "to see accuracy details here.")


# --------------------------------------------------------------------------- #
# How it works
# --------------------------------------------------------------------------- #
def architecture_tab(bundle):
    st.subheader("How it works")
    st.markdown("""
The app spots duplicates in two quick steps:

1. **Quick fingerprint check.** Every image gets a tiny "fingerprint" (a perceptual
   hash). Identical or barely-changed copies are matched instantly.
2. **AI look-alike check.** Each image is turned into a list of numbers by an AI
   vision model (**DINOv2**) that captures *what the picture looks like*. Images with
   close numbers are flagged as look-alikes — even after cropping, resizing,
   re-compression, or colour shifts. A fast similarity search (**FAISS**) compares
   them, and matches are grouped together.

The **Match strictness** slider in the sidebar simply decides how close two images
must be to count as a match.
    """)
    if bundle:
        m = bundle["manifest"]
        st.divider()
        st.caption("Sample library details")
        c1, c2, c3 = st.columns(3)
        c1.metric("Images", f"{m.get('n_images', 0):,}")
        c2.metric("Model", m.get("model_id", "—").split("/")[-1])
        c3.metric("Fingerprint size", f"{m.get('embedding_dim', '—')} numbers")
