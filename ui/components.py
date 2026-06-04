"""Theme, header, sidebar and small render helpers."""

import os

import streamlit as st

from config import CFG

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700;900&family=Inter:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');
.main {
    background: #0a0a1a;
    background-image:
        radial-gradient(at 20% 30%, rgba(139,92,246,0.15) 0px, transparent 50%),
        radial-gradient(at 80% 0%, rgba(168,85,247,0.12) 0px, transparent 50%),
        radial-gradient(at 60% 100%, rgba(236,72,153,0.12) 0px, transparent 50%);
    color: #e2e8f0;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1a1a3e 0%, #0f0f2e 100%);
    border-right: 2px solid rgba(139,92,246,0.3);
}
.main-header {
    font-family: 'Cinzel', serif; font-size: 3.6rem; font-weight: 900;
    text-align: center;
    background: linear-gradient(135deg,#6366f1 0%,#a855f7 35%,#ec4899 70%,#10b981 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    letter-spacing: 0.1em; margin-bottom: 0.2rem;
    filter: drop-shadow(0 0 24px rgba(168,85,247,0.45));
}
.subtitle {
    font-family: 'Cinzel', serif; font-size: 1rem; text-align: center;
    color: #a78bfa; letter-spacing: 0.15em; text-transform: uppercase;
    margin-bottom: 1.5rem; font-weight: 600;
}
.similarity-badge {
    display:inline-flex; padding: 0.35rem 0.9rem; border-radius: 50px;
    font-weight: 700; font-size: 0.8rem; font-family: 'Cinzel', serif;
}
.similarity-high { color:#10b981; border:2px solid #10b981;
    background: rgba(16,185,129,0.18); }
.similarity-medium { color:#a855f7; border:2px solid #a855f7;
    background: rgba(168,85,247,0.18); }
.similarity-low { color:#ef4444; border:2px solid #ef4444;
    background: rgba(239,68,68,0.18); }
.stButton > button {
    background: linear-gradient(135deg,#6366f1,#a855f7);
    border: 2px solid rgba(168,85,247,0.5); color: white;
    font-family: 'Cinzel', serif; font-weight: 600; border-radius: 10px;
}
.stTabs [data-baseweb="tab"] { font-family:'Cinzel',serif; font-weight:600; }
.stTabs [aria-selected="true"] { color:#a855f7; }
[data-testid="stMetricValue"] {
    font-family:'Cinzel',serif; font-weight:700;
    background: linear-gradient(135deg,#6366f1,#a855f7);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
}
</style>
"""


def apply_css():
    st.markdown(_CSS, unsafe_allow_html=True)


def render_header(mode_label):
    st.markdown(f"""
    <div style="text-align:center; margin-bottom:1.2rem;">
        <h1 class="main-header">MIRROR OF MAYA</h1>
        <p class="subtitle">Where Illusions Reveal Truth</p>
        <div style="color:#64748b; font-style:italic; font-size:0.85rem;">
            Near-duplicate image detection &mdash; DINOv2 &middot; FAISS &middot; dHash
        </div>
        <div style="color:#a78bfa; font-size:0.8rem; margin-top:0.4rem;">Mode: {mode_label}</div>
    </div>
    """, unsafe_allow_html=True)


def render_sidebar(bundle):
    with st.sidebar:
        st.markdown("### CONTROLS")
        st.markdown("---")

        st.markdown("**Engine**")
        st.caption(f"Model: `{CFG.MODEL_ID.split('/')[-1]}`  ·  Pooling: `{CFG.POOLING}`")
        st.caption(f"Device: `{_device_label()}`")

        st.markdown("---")
        st.markdown("**Similarity threshold**")
        st.session_state.threshold = st.slider(
            "Cosine cutoff", CFG.MIN_THRESHOLD, CFG.MAX_THRESHOLD,
            float(st.session_state.threshold), 0.01,
            help="Higher = stricter (fewer false positives).",
        )

        st.markdown("---")
        if bundle:
            m = bundle["manifest"]
            calib = bundle.get("calibration", {})
            st.markdown("**Corpus bundle**")
            st.metric("Indexed images", f"{m.get('n_images', 0):,}")
            if calib:
                st.metric("Calibrated F1", f"{calib.get('f1', 0):.3f}")
                st.caption(f"Optimal threshold: {calib.get('optimal_threshold', 0):.2f}")
            st.caption(f"Built: {m.get('created_at', '')[:19]}")
        else:
            st.info("No prebuilt corpus loaded — running in **stateless** mode. "
                    "Use the **Upload & Dedup** and **Versus** tabs.")


def _device_label():
    try:
        from embedder import get_device
        return get_device().upper()
    except Exception:
        return "CPU"


def similarity_class(score):
    if score >= 0.95:
        return "similarity-high"
    if score >= 0.85:
        return "similarity-medium"
    return "similarity-low"


def badge(score):
    return (f'<span class="similarity-badge {similarity_class(score)}">'
            f'{score * 100:.0f}%</span>')


def short_path(path):
    if not path:
        return ""
    parent = os.path.basename(os.path.dirname(path))
    return f"{parent}/{os.path.basename(path)}" if parent else os.path.basename(path)
