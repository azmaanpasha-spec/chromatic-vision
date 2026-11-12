"""Sidebar: brand, navigation and live session summary."""

from __future__ import annotations

import streamlit as st

from .state import PAGES, go_to
from .ui_components import icon, render


def render_sidebar() -> None:
    """Brand and navigation (drawn before the page content)."""
    with st.sidebar:
        render(
            f'<div class="cv-brand"><div class="cv-brand-logo" style="color:white">{icon("logo", 24, 2)}</div>'
            '<div><div class="cv-brand-name">Chromatic Vision</div>'
            '<div class="cv-brand-tag">See Beyond Colors. Understand Every Frame.</div></div></div>'
        )
        render('<div class="cv-nav-label">Workspace</div>')

        current = st.session_state.page
        for key, (title, material_icon) in PAGES.items():
            st.button(
                title,
                key=f"nav_{key}",
                icon=material_icon,
                type="primary" if key == current else "secondary",
                on_click=go_to,
                args=(key,),
                width="stretch",
            )


def render_sidebar_stats() -> None:
    """Session summary - drawn AFTER the page so it includes the latest run."""
    s = st.session_state.stats
    with st.sidebar:
        render(
            '<div class="cv-side-stats"><div class="cv-nav-label" style="margin:0 0 6px 0">This session</div>'
            f'<div class="row"><span>Images analysed</span><b>{s["images"]}</b></div>'
            f'<div class="row"><span>Videos processed</span><b>{s["videos"]}</b></div>'
            f'<div class="row"><span>Objects detected</span><b>{s["objects"]:,}</b></div>'
            f'<div class="row"><span>Frames analysed</span><b>{s["frames"]:,}</b></div></div>'
            '<div class="cv-side-foot">Image &amp; Video Analytics mini-project<br>'
            'Python · OpenCV · Streamlit</div>'
        )
