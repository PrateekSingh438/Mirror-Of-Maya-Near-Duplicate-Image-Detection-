"""Streamlit session-state defaults. No disk persistence (deploy is ephemeral)."""

import streamlit as st

from config import CFG


def init_state():
    defaults = {
        "threshold": CFG.DEFAULT_THRESHOLD,   # active threshold (search / Mode B)
        "mb_result": None,                    # last stateless dedup result
        "mb_images": {},                      # label -> raw bytes for display
        "mb_remove": set(),                   # labels marked as duplicates
        "manager_page": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
