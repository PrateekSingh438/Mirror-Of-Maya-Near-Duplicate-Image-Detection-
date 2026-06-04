"""Mirror of Maya — serving app (Streamlit shell).

No dataset on disk is required. Mode A loads a prebuilt artifact bundle (local /
HF / URL); Mode B dedups uploads in memory. The shell just wires modes to tabs.
"""

import streamlit as st

from artifacts import load_bundle
from config import CFG
from ui.components import apply_css, render_header, render_sidebar
from ui.session import init_state
from ui.tabs import (analytics_tab, architecture_tab, manager_tab,
                     search_tab, upload_dedup_tab, versus_tab)

st.set_page_config(page_title=CFG.PAGE_TITLE, layout=CFG.LAYOUT,
                   initial_sidebar_state="expanded")
apply_css()
init_state()


@st.cache_resource(show_spinner="Loading corpus bundle…")
def get_bundle():
    try:
        return load_bundle(CFG)
    except ValueError as e:
        st.error(str(e))
        return None


bundle = get_bundle()

render_header()
render_sidebar(bundle)

tab_names = ["Find Duplicates", "Search by Image", "Duplicate Groups",
             "Compare Two", "Accuracy", "How It Works"]
tabs = st.tabs(tab_names)
with tabs[0]:
    upload_dedup_tab()
with tabs[1]:
    search_tab(bundle)
with tabs[2]:
    manager_tab(bundle)
with tabs[3]:
    versus_tab()
with tabs[4]:
    analytics_tab(bundle)
with tabs[5]:
    architecture_tab(bundle)

st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#6b7488;font-size:0.8rem;padding:0.8rem;'>"
    "Mirror of Maya · finds duplicate &amp; near-identical images</div>",
    unsafe_allow_html=True,
)
