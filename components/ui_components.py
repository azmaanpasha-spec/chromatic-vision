"""
Reusable HTML/CSS building blocks for the Chromatic Vision interface.

All components render static HTML through st.html / st.markdown - they do
not contain fake buttons. Interactive controls are always real Streamlit
widgets.
"""

from __future__ import annotations

import html
import os
from typing import Iterable, List, Optional, Sequence, Tuple

import streamlit as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# Icons (stroke icons drawn in the style of the open-source Lucide set)
# ---------------------------------------------------------------------------
_ICON_PATHS = {
    "logo": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3.2"/><path d="M12 3v5.8M20.2 8.2l-5.1 2.6M18.4 18.6l-4.3-4.2M5.6 18.6l4.3-4.2M3.8 8.2l5.1 2.6"/>',
    "home": '<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/><path d="M10 21v-6h4v6"/>',
    "image": '<rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.1-3.1a2 2 0 0 0-2.8 0L6 21"/>',
    "video": '<rect x="2" y="6" width="14" height="12" rx="2.5"/><path d="m16 10.5 6-3.5v10l-6-3.5"/>',
    "chart": '<path d="M3 3v18h18"/><path d="M7 15l4-5 3 3 5-7"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6"/><path d="M12 7.5h.01"/>',
    "palette": '<circle cx="13.5" cy="6.5" r="1.3"/><circle cx="17.5" cy="10.5" r="1.3"/><circle cx="8.5" cy="7.5" r="1.3"/><circle cx="6.5" cy="12.5" r="1.3"/><path d="M12 2a10 10 0 0 0 0 20c1.1 0 2-.9 2-2 0-.5-.2-1-.5-1.3-.3-.4-.5-.8-.5-1.3 0-1.1.9-2 2-2h2.4A5.6 5.6 0 0 0 22 9.8C22 5.5 17.5 2 12 2z"/>',
    "layers": '<path d="m12 2 10 5-10 5L2 7z"/><path d="m2 12 10 5 10-5"/><path d="m2 17 10 5 10-5"/>',
    "target": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
    "scan": '<path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/><rect x="7" y="7" width="10" height="10" rx="1.5"/>',
    "activity": '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    "route": '<circle cx="6" cy="19" r="2.5"/><circle cx="18" cy="5" r="2.5"/><path d="M8.5 19H17a3.5 3.5 0 0 0 0-7H7a3.5 3.5 0 0 1 0-7h8.5"/>',
    "film": '<rect x="3" y="3" width="18" height="18" rx="2.5"/><path d="M7 3v18M17 3v18M3 8h4M3 16h4M17 8h4M17 16h4M3 12h18"/>',
    "frames": '<rect x="3" y="5" width="7" height="14" rx="1.5"/><rect x="14" y="5" width="7" height="14" rx="1.5"/>',
    "box": '<path d="M21 8 12 3 3 8v8l9 5 9-5z"/><path d="m3 8 9 5 9-5M12 13v8"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "percent": '<path d="M19 5 5 19"/><circle cx="6.5" cy="6.5" r="2.5"/><circle cx="17.5" cy="17.5" r="2.5"/>',
    "ruler": '<path d="M3 17 17 3l4 4L7 21z"/><path d="m7.5 12.5 2 2M10.5 9.5l2 2M13.5 6.5l2 2"/>',
    "upload": '<path d="M12 16V4M7 9l5-5 5 5"/><path d="M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3"/>',
    "zap": '<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>',
    "gauge": '<path d="M12 14l4-4"/><path d="M3.3 17a9 9 0 1 1 17.4 0"/>',
    "sparkles": '<path d="M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8z"/><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z"/>',
    "grid": '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    "cpu": '<rect x="5" y="5" width="14" height="14" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/>',
    "book": '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V3H6.5A2.5 2.5 0 0 0 4 5.5z"/><path d="M4 19.5A2.5 2.5 0 0 0 6.5 22H20v-5"/>',
}


def icon(name: str, size: int = 20, stroke: float = 1.8) -> str:
    """Return an inline SVG icon."""
    path = _ICON_PATHS.get(name, _ICON_PATHS["info"])
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" '
            f'fill="none" stroke="currentColor" stroke-width="{stroke}" stroke-linecap="round" '
            f'stroke-linejoin="round">{path}</svg>')


# Accent presets for icon tiles: (background, foreground, glow)
TONES = {
    "indigo": ("rgba(99,102,241,0.16)", "#A5B4FC", "rgba(99,102,241,0.28)"),
    "sky": ("rgba(56,189,248,0.14)", "#7DD3FC", "rgba(56,189,248,0.24)"),
    "violet": ("rgba(167,139,250,0.16)", "#C4B5FD", "rgba(167,139,250,0.26)"),
    "green": ("rgba(34,197,94,0.14)", "#86EFAC", "rgba(34,197,94,0.22)"),
    "amber": ("rgba(245,158,11,0.14)", "#FCD34D", "rgba(245,158,11,0.22)"),
    "rose": ("rgba(239,68,68,0.14)", "#FCA5A5", "rgba(239,68,68,0.22)"),
}


def _tone_style(tone: str) -> str:
    bg, fg, glow = TONES.get(tone, TONES["indigo"])
    return f"--icon-bg:{bg};--icon-fg:{fg};--glow:{glow};"


# ---------------------------------------------------------------------------
# Global CSS
# ---------------------------------------------------------------------------
def load_css() -> None:
    """Inject styles/main.css into the page."""
    path = os.path.join(ROOT, "styles", "main.css")
    with open(path, "r", encoding="utf-8") as fh:
        css = fh.read()
    st.html(f"<style>{css}</style>")


def render(markup: str) -> None:
    """Render trusted, app-generated HTML."""
    st.markdown(markup, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Components
# ---------------------------------------------------------------------------
def page_header(title: str, subtitle: str, icon_name: str, eyebrow: str = "") -> None:
    render(
        f'<div class="cv-header"><div class="cv-header-icon">{icon(icon_name, 24)}</div>'
        f'<div><div class="cv-eyebrow">{html.escape(eyebrow)}</div><h1>{html.escape(title)}</h1>'
        f'<p>{html.escape(subtitle)}</p></div></div>'
    )


def stat_card(label: str, value, icon_name: str, tone: str = "indigo", sub: str = "",
              small: bool = False) -> str:
    """Return HTML for one metric card (combine several inside stat_grid)."""
    value_cls = "cv-stat-value sm" if small else "cv-stat-value"
    sub_html = f'<div class="cv-stat-sub">{html.escape(sub)}</div>' if sub else ""
    return (f'<div class="cv-stat" style="{_tone_style(tone)}"><div class="cv-stat-top">'
            f'<div class="cv-stat-label">{html.escape(label)}</div>'
            f'<div class="cv-stat-icon">{icon(icon_name, 18)}</div></div>'
            f'<div class="{value_cls}">{html.escape(str(value))}</div>{sub_html}</div>')


def stat_grid(cards: Iterable[str], min_width: int = 190) -> None:
    render(f'<div class="cv-grid" style="grid-template-columns:repeat(auto-fit,minmax({min_width}px,1fr))">'
           f'{"".join(cards)}</div>')


def feature_card(title: str, text: str, icon_name: str, tone: str = "indigo") -> str:
    return (f'<div class="cv-feature" style="{_tone_style(tone)}"><div class="cv-feature-icon">'
            f'{icon(icon_name, 22)}</div><h4>{html.escape(title)}</h4><p>{html.escape(text)}</p></div>')


def feature_grid(cards: Iterable[str]) -> None:
    render(f'<div class="cv-feature-grid">{"".join(cards)}</div>')


def section_title(title: str, note: str = "") -> None:
    render(f'<div class="cv-section"><h3>{html.escape(title)}</h3><span>{html.escape(note)}</span></div>')


def card_title(title: str, icon_name: str, note: str = "") -> None:
    note_html = f"<small>{html.escape(note)}</small>" if note else ""
    render(f'<div class="cv-card-title"><span class="ic">{icon(icon_name, 18)}</span>'
           f'<b>{html.escape(title)}</b>{note_html}</div>')


def empty_state(title: str, text: str, icon_name: str = "upload") -> None:
    render(f'<div class="cv-empty"><div class="ic">{icon(icon_name, 28)}</div>'
           f'<h4>{html.escape(title)}</h4><p>{html.escape(text)}</p></div>')


def label(text: str) -> None:
    render(f'<div class="cv-label">{html.escape(text)}</div>')


def chips(items: Sequence[Tuple[str, str]]) -> None:
    """items: list of (text, kind) where kind is '', 'ok' or 'warn'."""
    render("".join(f'<span class="cv-chip {k}">{html.escape(t)}</span>' for t, k in items))


def color_swatch(name: str, hex_color: str, range_text: str, hue_spans: List[Tuple[int, int]]) -> None:
    """Swatch with the active HSV range and a hue bar showing the selected band(s)."""
    sel = "".join(
        f'<div class="sel" style="left:{lo / 179 * 100:.2f}%;width:{max(1.2, (hi - lo) / 179 * 100):.2f}%"></div>'
        for lo, hi in hue_spans
    )
    render(
        f'<div class="cv-swatch-row"><div class="cv-swatch" style="background:{hex_color}"></div>'
        f'<div class="cv-swatch-meta"><b>{html.escape(name)}</b>'
        + "".join(f"<code>{html.escape(part.strip())}</code><br>" for part in range_text.split("+"))
        + '</div></div>'
        f'<div class="cv-hue-bar">{sel}</div>'
    )


def flow_diagram(steps: Sequence[Tuple[str, str, str]]) -> None:
    """Horizontal workflow diagram: steps = [(title, description, code), ...]."""
    parts = []
    for i, (title, desc, code) in enumerate(steps, start=1):
        code_html = f"<code>{html.escape(code)}</code>" if code else ""
        parts.append(f'<div class="cv-flow-step"><div class="n">STEP {i:02d}</div><b>{html.escape(title)}</b>'
                     f'<span>{html.escape(desc)}</span>{code_html}</div>')
        if i < len(steps):
            parts.append('<div class="cv-flow-arrow">→</div>')
    render(f'<div class="cv-flow">{"".join(parts)}</div>')


def show_figure(fig, key: Optional[str] = None) -> None:
    """Display a Plotly figure with our own theme (not Streamlit's)."""
    st.plotly_chart(fig, theme=None, key=key, config={"displaylogo": False, "displayModeBar": False})
