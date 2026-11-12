"""
Analytics helpers: every number here is computed from the actual image or
video processing results - nothing is simulated.

Contains
    * color_distribution  - share of pixels per colour family (HSV based)
    * hue_histogram       - raw hue histogram of coloured pixels
    * Plotly figure builders with the Chromatic Vision dark theme
    * a Matplotlib hue-spectrum figure
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import cv2
import matplotlib

matplotlib.use("Agg")  # headless backend - no GUI windows
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import plotly.graph_objects as go  # noqa: E402

# Theme constants (match styles/main.css)
BG = "rgba(0,0,0,0)"
CARD = "#151D30"
GRID = "rgba(148,163,184,0.12)"
TEXT = "#F8FAFC"
MUTED = "#94A3B8"
ACCENT = "#6366F1"
ACCENT_2 = "#38BDF8"
HIGHLIGHT = "#A78BFA"

# Colour families used for the distribution chart, with OpenCV hue bounds.
FAMILY_COLORS = {
    "Red": "#EF4444", "Orange": "#F97316", "Yellow": "#FACC15", "Green": "#22C55E",
    "Cyan": "#22D3EE", "Blue": "#3B82F6", "Purple": "#A855F7", "Pink": "#EC4899",
    "White": "#E2E8F0", "Gray": "#64748B", "Black": "#1E293B",
}
HUE_FAMILIES = [
    ("Red", 0, 10), ("Orange", 11, 20), ("Yellow", 21, 34), ("Green", 35, 85),
    ("Cyan", 86, 94), ("Blue", 95, 128), ("Purple", 129, 160), ("Pink", 161, 169),
    ("Red", 170, 179),
]


# ---------------------------------------------------------------------------
# Calculations
# ---------------------------------------------------------------------------
def _sample(hsv: np.ndarray, max_pixels: int = 250_000) -> np.ndarray:
    """Return an (N, 3) array of HSV pixels, subsampled for speed."""
    pixels = hsv.reshape(-1, 3)
    step = max(1, len(pixels) // max_pixels)
    return pixels[::step]


def color_distribution(image_bgr: np.ndarray, s_threshold: int = 50,
                       v_dark: int = 50, v_white: int = 200) -> Dict[str, float]:
    """Percentage of pixels belonging to each colour family.

    Achromatic pixels are separated first:
        V < v_dark                       -> Black
        S < s_threshold and V > v_white  -> White
        S < s_threshold                  -> Gray
    Remaining (coloured) pixels are grouped by hue.
    """
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    px = _sample(hsv).astype(np.int32)
    h, s, v = px[:, 0], px[:, 1], px[:, 2]
    total = float(len(px))

    black = v < v_dark
    low_sat = (s < s_threshold) & ~black
    white = low_sat & (v > v_white)
    gray = low_sat & ~white
    chroma = ~(black | low_sat)

    result: Dict[str, float] = {name: 0.0 for name in FAMILY_COLORS}
    result["Black"] = 100.0 * black.sum() / total
    result["White"] = 100.0 * white.sum() / total
    result["Gray"] = 100.0 * gray.sum() / total
    for name, lo, hi in HUE_FAMILIES:
        result[name] += 100.0 * (chroma & (h >= lo) & (h <= hi)).sum() / total
    return result


def hue_histogram(image_bgr: np.ndarray, s_threshold: int = 50, v_dark: int = 50) -> np.ndarray:
    """180-bin histogram of the hue channel for coloured pixels only."""
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (0, s_threshold, v_dark), (179, 255, 255))
    hist = cv2.calcHist([hsv], [0], mask, [180], [0, 180]).flatten()
    return hist


# ---------------------------------------------------------------------------
# Plotly figures
# ---------------------------------------------------------------------------
def _style(fig: go.Figure, height: int = 340, title: Optional[str] = None) -> go.Figure:
    fig.update_layout(
        height=height,
        title=dict(text=title, font=dict(size=14, color=TEXT)) if title else None,
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        font=dict(family="Inter, Segoe UI, sans-serif", color=MUTED, size=12),
        margin=dict(l=70, r=20, t=40 if title else 16, b=60),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=MUTED)),
        hoverlabel=dict(bgcolor=CARD, font_color=TEXT, bordercolor="#334155"),
    )
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID, automargin=True,
                     title_standoff=12)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID, automargin=True,
                     title_standoff=12)
    return fig


def distribution_donut(dist: Dict[str, float], highlight: Optional[str] = None,
                       min_percent: float = 0.5) -> go.Figure:
    """Donut chart of colour families (tiny slices merged into 'Other')."""
    items = sorted(dist.items(), key=lambda kv: kv[1], reverse=True)
    labels, values, colors = [], [], []
    other = 0.0
    for name, pct in items:
        if pct < min_percent:
            other += pct
            continue
        labels.append(name)
        values.append(round(pct, 2))
        colors.append(FAMILY_COLORS[name])
    if other > 0:
        labels.append("Other")
        values.append(round(other, 2))
        colors.append("#334155")
    pull = [0.08 if lbl == highlight else 0 for lbl in labels]
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.62, pull=pull, sort=False,
        marker=dict(colors=colors, line=dict(color="#0B1020", width=2)),
        textinfo="percent", textfont=dict(color="#0B1020", size=11),
        hovertemplate="%{label}: %{value:.2f}% of pixels<extra></extra>",
    ))
    if highlight and highlight in dist:
        fig.add_annotation(text=f"<b>{dist[highlight]:.1f}%</b><br><span style='font-size:11px'>{highlight}</span>",
                           showarrow=False, font=dict(size=20, color=TEXT))
    return _style(fig, 330)


def distribution_bar(dist: Dict[str, float], highlight: Optional[str] = None) -> go.Figure:
    """Horizontal bar chart of colour families, selected colour emphasised."""
    items = sorted(dist.items(), key=lambda kv: kv[1])
    names = [k for k, _ in items]
    vals = [v for _, v in items]
    opacity = [1.0 if (highlight is None or n == highlight) else 0.55 for n in names]
    fig = go.Figure(go.Bar(
        x=vals, y=names, orientation="h",
        marker=dict(color=[FAMILY_COLORS[n] for n in names], opacity=opacity,
                    line=dict(color=[TEXT if n == highlight else "rgba(0,0,0,0)" for n in names], width=1.5)),
        text=[f"{v:.1f}%" for v in vals], textposition="outside", textfont=dict(color=MUTED),
        hovertemplate="%{y}: %{x:.2f}%<extra></extra>",
    ))
    fig.update_xaxes(title="Share of pixels (%)", range=[0, max(vals + [1]) * 1.18])
    return _style(fig, 360)


def objects_area_bar(objects: Sequence, color_hex: str) -> go.Figure:
    """Bar chart of the pixel area of each detected object."""
    ids = [f"#{o.object_id}" for o in objects]
    areas = [o.area for o in objects]
    fig = go.Figure(go.Bar(
        x=ids, y=areas, marker=dict(color=color_hex, line=dict(width=0)),
        hovertemplate="Object %{x}<br>Area: %{y:,.0f} px<extra></extra>",
    ))
    fig.update_xaxes(title="Detected object", type="category")
    fig.update_yaxes(title="Area (pixels)")
    return _style(fig, 320)


def history_bar(history: List[Dict]) -> go.Figure:
    """Objects detected in each image analysis run of this session."""
    labels = [f"Run {i + 1}<br>{h['color']}" for i, h in enumerate(history)]
    fig = go.Figure(go.Bar(
        x=labels, y=[h["objects"] for h in history],
        marker=dict(color=[h["hex"] for h in history]),
        hovertemplate="%{x}<br>Objects: %{y}<extra></extra>",
    ))
    fig.update_yaxes(title="Objects detected", rangemode="tozero", dtick=1)
    return _style(fig, 300)


def objects_per_frame(per_frame: List[Dict], color_hex: str = ACCENT_2) -> go.Figure:
    frames = [r["Frame"] for r in per_frame]
    counts = [r["Objects"] for r in per_frame]
    fig = go.Figure(go.Scatter(
        x=frames, y=counts, mode="lines", line=dict(color=color_hex, width=2, shape="hv"),
        fill="tozeroy", fillcolor="rgba(56,189,248,0.12)",
        hovertemplate="Frame %{x}<br>Objects: %{y}<extra></extra>",
    ))
    fig.update_xaxes(title="Frame")
    fig.update_yaxes(title="Objects detected", rangemode="tozero", dtick=1)
    return _style(fig, 300)


def processing_time_chart(per_frame: List[Dict]) -> go.Figure:
    frames = [r["Frame"] for r in per_frame]
    times = [r["Processing (ms)"] for r in per_frame]
    avg = float(np.mean(times)) if times else 0.0
    fig = go.Figure(go.Scatter(
        x=frames, y=times, mode="lines", line=dict(color=HIGHLIGHT, width=1.5),
        hovertemplate="Frame %{x}<br>%{y:.2f} ms<extra></extra>", name="Per frame",
    ))
    fig.add_hline(y=avg, line=dict(color=ACCENT_2, dash="dash", width=1),
                  annotation_text=f"avg {avg:.2f} ms", annotation_font_color=ACCENT_2)
    fig.update_xaxes(title="Frame")
    # The first frame(s) include one-off codec/initialisation cost. Scale the axis to the
    # 99th percentile so normal frames stay readable; the spike is still plotted (clipped).
    if times:
        top = float(np.percentile(times, 99)) * 1.35
        fig.update_yaxes(range=[0, max(top, avg * 1.5, 1.0)])
    fig.update_yaxes(title="Processing time (ms)")
    return _style(fig, 300)


def trajectory_chart(paths: Dict[int, List], width: int, height: int,
                     min_points: int = 3) -> go.Figure:
    """Centroid paths of every track drawn in image coordinates."""
    palette = ["#6366F1", "#38BDF8", "#A78BFA", "#22C55E", "#F59E0B", "#EF4444",
               "#EC4899", "#14B8A6", "#84CC16", "#F97316"]
    fig = go.Figure()
    for i, (tid, path) in enumerate(sorted(paths.items())):
        if len(path) < min_points:
            continue
        xs = [p[1] for p in path]
        ys = [p[2] for p in path]
        color = palette[(tid - 1) % len(palette)]
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", name=f"ID {tid}", line=dict(color=color, width=2),
            customdata=[p[0] + 1 for p in path],
            hovertemplate=f"ID {tid}<br>Frame %{{customdata}}<br>x=%{{x}}, y=%{{y}}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(x=[xs[0]], y=[ys[0]], mode="markers", showlegend=False,
                                 marker=dict(color=color, size=9, symbol="circle-open", line=dict(width=2)),
                                 hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=[xs[-1]], y=[ys[-1]], mode="markers", showlegend=False,
                                 marker=dict(color=color, size=9), hoverinfo="skip"))
    fig.update_xaxes(range=[0, width], title="x (px)", constrain="domain")
    fig.update_yaxes(range=[height, 0], title="y (px)", scaleanchor="x", scaleratio=1, constrain="domain")
    return _style(fig, 380)


def track_lifetime_chart(tracks: List[Dict]) -> go.Figure:
    """Gantt-like bar per track: from first to last frame seen."""
    palette = ["#6366F1", "#38BDF8", "#A78BFA", "#22C55E", "#F59E0B", "#EF4444",
               "#EC4899", "#14B8A6", "#84CC16", "#F97316"]
    tracks = sorted(tracks, key=lambda t: t["Track ID"])
    fig = go.Figure(go.Bar(
        y=[f"ID {t['Track ID']}" for t in tracks],
        x=[t["Last frame"] - t["First frame"] + 1 for t in tracks],
        base=[t["First frame"] + 1 for t in tracks],
        orientation="h",
        marker=dict(color=[palette[(t["Track ID"] - 1) % len(palette)] for t in tracks]),
        customdata=[[t["First frame"] + 1, t["Last frame"] + 1, t["Frames seen"]] for t in tracks],
        hovertemplate="%{y}<br>Frames %{customdata[0]}-%{customdata[1]}"
                      "<br>Detected in %{customdata[2]} frames<extra></extra>",
    ))
    fig.update_xaxes(title="Frame")
    fig.update_yaxes(autorange="reversed", type="category")
    return _style(fig, max(220, 36 * len(tracks) + 80))


# ---------------------------------------------------------------------------
# Matplotlib figure
# ---------------------------------------------------------------------------
def hue_spectrum_figure(image_bgr: np.ndarray, ranges: Sequence = ()) -> plt.Figure:
    """Matplotlib bar chart of the hue histogram, each bar drawn in its own hue.

    Shaded bands show the HSV hue ranges used for the selected colour.
    """
    hist = hue_histogram(image_bgr)
    total = hist.sum()
    hist = hist / total * 100.0 if total > 0 else hist

    hues = np.arange(180, dtype=np.uint8)
    hsv_row = np.stack([hues, np.full(180, 230, np.uint8), np.full(180, 255, np.uint8)], axis=1)
    rgb = cv2.cvtColor(hsv_row.reshape(1, 180, 3), cv2.COLOR_HSV2RGB).reshape(180, 3) / 255.0

    fig, ax = plt.subplots(figsize=(8, 2.8), dpi=130)
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")
    for lo, hi in ranges:
        ax.axvspan(lo[0] - 0.5, hi[0] + 0.5, color="#6366F1", alpha=0.18, lw=0)
    ax.bar(hues, hist, width=1.0, color=rgb, edgecolor="none")
    ax.set_xlim(-0.5, 179.5)
    ax.set_xlabel("Hue (OpenCV scale 0–179)", color=MUTED, fontsize=9)
    ax.set_ylabel("% of coloured pixels", color=MUTED, fontsize=9)
    ax.tick_params(colors=MUTED, labelsize=8)
    for spine in ax.spines.values():
        spine.set_color("#334155")
    ax.grid(axis="y", color="#334155", alpha=0.4, lw=0.6)
    ax.set_axisbelow(True)
    fig.tight_layout()
    return fig
