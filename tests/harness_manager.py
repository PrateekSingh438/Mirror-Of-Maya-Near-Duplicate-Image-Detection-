"""AppTest harness (not a test module): renders the Manager tab with
fabricated duplicate pairs so the selection UI can be exercised headlessly,
with no detector and no model. Run via streamlit.testing.v1.AppTest."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st
from PIL import Image

import tabs
from session_manager import initialize_session_state

IMG_DIR = os.path.join(tempfile.gettempdir(), "maya_manager_harness")


def make_images():
    os.makedirs(IMG_DIR, exist_ok=True)
    paths = []
    for name, color in [("a1.jpg", (200, 30, 30)), ("a2.jpg", (210, 40, 40)),
                        ("a3.jpg", (220, 50, 50)), ("b1.jpg", (30, 30, 200)),
                        ("b2.jpg", (40, 40, 210))]:
        p = os.path.join(IMG_DIR, name)
        if not os.path.exists(p):
            Image.new("RGB", (64, 64), color).save(p)
        paths.append(p)
    return paths


paths = make_images()
initialize_session_state()

# Two clusters: {a1, a2, a3} and {b1, b2} -> 3 deletable duplicates total
fake = [
    {"file1": paths[0], "file2": paths[1], "score": 0.97, "method": "DINOv2"},
    {"file1": paths[0], "file2": paths[2], "score": 0.95, "method": "DINOv2"},
    {"file1": paths[3], "file2": paths[4], "score": 0.99, "method": "dHash"},
]
st.session_state.duplicates = fake
st.session_state.all_duplicates = fake
st.session_state.demo_mode = False

tabs.manager_tab()
