"""Theme, header, sidebar and small render helpers (plain-language UI)."""

import os

import streamlit as st

from config import CFG

# CSS targets current Streamlit selectors (.stApp, stSidebar, stTabs). The title
# has a solid fallback colour so it stays visible even if the gradient clip
# doesn't paint in a given browser.
_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp {
    background:
        radial-gradient(1200px 600px at 15% -10%, rgba(124,58,237,0.18), transparent 60%),
        radial-gradient(1000px 500px at 95% 0%, rgba(236,72,153,0.12), transparent 55%),
        #0b1020;
    color: #e6e9f2;
}
section[data-testid="stSidebar"] {
    background: #11162a;
    border-right: 1px solid rgba(148,163,184,0.18);
}
section[data-testid="stSidebar"] * { color: #d7dcea; }

.mom-title {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    font-size: 2.7rem;
    line-height: 1.1;
    margin: 0;
    text-align: center;
    color: #c4b5fd; /* visible fallback */
    background: linear-gradient(90deg, #818cf8, #c084fc 45%, #f472b6);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
}
.mom-tagline {
    text-align: center; color: #aab2c5; font-size: 1.05rem;
    margin: 0.35rem 0 0.1rem 0;
}
.mom-sub {
    text-align: center; color: #6b7488; font-size: 0.82rem; margin-bottom: 0.4rem;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] { gap: 0.25rem; }
.stTabs [data-baseweb="tab"] {
    font-weight: 600; color: #97a0b5; border-radius: 8px 8px 0 0;
}
.stTabs [aria-selected="true"] { color: #c4b5fd; }

/* Buttons */
.stButton > button, .stDownloadButton > button {
    border-radius: 10px; font-weight: 600; border: 1px solid rgba(148,163,184,0.25);
}
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
    background: linear-gradient(90deg, #6d5efc, #a855f7); border: none; color: #fff;
}

/* Metric cards */
[data-testid="stMetric"] {
    background: rgba(148,163,184,0.07);
    border: 1px solid rgba(148,163,184,0.16);
    padding: 0.8rem 1rem; border-radius: 12px;
}
[data-testid="stMetricValue"] { color: #ffffff; font-weight: 700; }

/* Similarity pill shown under images */
.match-pill {
    display: inline-block; padding: 0.15rem 0.6rem; border-radius: 999px;
    font-size: 0.78rem; font-weight: 700;
}
.match-strong { background: rgba(16,185,129,0.18); color: #34d399; border: 1px solid #34d399; }
.match-mid    { background: rgba(168,85,247,0.18); color: #c084fc; border: 1px solid #c084fc; }
.match-weak   { background: rgba(245,158,11,0.18); color: #fbbf24; border: 1px solid #fbbf24; }
</style>
"""


def apply_css():
    st.markdown(_CSS, unsafe_allow_html=True)


def render_header():
    st.markdown("""
    <div style="margin: 0.2rem 0 1rem 0;">
        <h1 class="mom-title">Mirror of Maya</h1>
        <p class="mom-tagline">Find duplicate and near-identical images</p>
        <p class="mom-sub">Catches the same picture even after resizing, cropping, re-compression, or colour changes</p>
    </div>
    """, unsafe_allow_html=True)


def render_sidebar(bundle):
    with st.sidebar:
        st.markdown("### Settings")

        # Friendly match-strictness control (stored as a cosine cutoff).
        st.markdown("**Match strictness**")
        st.session_state.threshold = st.slider(
            "How similar must two images be to count as a match?",
            CFG.MIN_THRESHOLD, CFG.MAX_THRESHOLD, float(st.session_state.threshold), 0.01,
            help="Lower = catches more look-alikes (but a few false matches). "
                 "Higher = only near-identical images count.",
            label_visibility="visible",
        )
        st.caption(f"Currently: **{_strictness_word(st.session_state.threshold)}** "
                   f"({st.session_state.threshold:.2f})")

        st.divider()
        if bundle:
            m = bundle["manifest"]
            calib = bundle.get("calibration", {})
            st.markdown("**Sample image library**")
            st.caption(f"{m.get('n_images', 0):,} images are loaded and ready to "
                       "search and browse.")
            if calib:
                st.caption(f"Best accuracy is around strictness "
                           f"{calib.get('optimal_threshold', 0):.2f}.")
        else:
            st.info("No sample library is loaded. Head to **Find Duplicates** and "
                    "upload your own images to begin.")

        st.divider()
        with st.expander("Technical details"):
            st.caption(f"Model: {CFG.MODEL_ID.split('/')[-1]} (DINOv2)")
            st.caption(f"Pooling: {CFG.POOLING} · Running on: {_device_label()}")


def _strictness_word(t):
    if t >= 0.85:
        return "Very strict"
    if t >= 0.7:
        return "Strict"
    if t >= 0.55:
        return "Balanced"
    return "Loose"


def _device_label():
    try:
        from embedder import get_device
        return "GPU" if get_device() == "cuda" else "CPU"
    except Exception:
        return "CPU"


def similarity_class(score):
    if score >= 0.9:
        return "match-strong"
    if score >= 0.7:
        return "match-mid"
    return "match-weak"


def badge(score):
    return (f'<span class="match-pill {similarity_class(score)}">'
            f'{score * 100:.0f}% match</span>')


def short_path(path):
    if not path:
        return ""
    parent = os.path.basename(os.path.dirname(path))
    return f"{parent}/{os.path.basename(path)}" if parent else os.path.basename(path)
