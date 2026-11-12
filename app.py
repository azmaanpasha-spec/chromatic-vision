"""
Chromatic Vision - Intelligent Color Detection and Object Tracking
Using Image Processing Techniques.

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import os

import streamlit as st

from components.sidebar import render_sidebar, render_sidebar_stats
from components.state import init_state
from components.ui_components import load_css

ROOT = os.path.dirname(os.path.abspath(__file__))
LOGO = os.path.join(ROOT, "assets", "logo.png")

st.set_page_config(
    page_title="Chromatic Vision · Image & Video Analytics",
    page_icon=LOGO if os.path.exists(LOGO) else "🎯",
    layout="wide",
    initial_sidebar_state="auto",  # open on desktop, collapsed on phones

)


def main() -> None:
    load_css()
    init_state()
    render_sidebar()

    page = st.session_state.page
    # Pages are imported lazily so a problem in one page cannot break the others.
    if page == "image":
        from views.image_studio import render_image_studio
        render_image_studio()
    elif page == "video":
        from views.video_studio import render_video_studio
        render_video_studio()
    elif page == "analytics":
        from views.analytics_page import render_analytics
        render_analytics()
    elif page == "about":
        from views.about import render_about
        render_about()
    else:
        from views.overview import render_overview
        render_overview()

    render_sidebar_stats()


main()
