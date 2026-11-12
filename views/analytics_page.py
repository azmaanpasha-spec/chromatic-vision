"""Analytics & Insights: charts computed from the latest image and video results."""

from __future__ import annotations

from typing import Optional

import matplotlib.pyplot as plt
import streamlit as st

from components.state import go_to
from components.ui_components import (card_title, empty_state, page_header, section_title, show_figure,
                                      stat_card, stat_grid)
from modules import analytics
from modules.image_processing import ImageAnalysisResult, bgr_to_rgb
from modules.video_processing import VideoAnalysisResult


@st.cache_data(show_spinner=False, max_entries=8)
def _distribution(run_key: str, _image) -> dict:
    """Colour distribution, cached per analysis run (run_key identifies the run;
    the leading underscore tells Streamlit not to hash the large image array)."""
    return analytics.color_distribution(_image)


def render_analytics() -> None:
    page_header("Analytics & Insights",
                "Every metric and chart on this page is calculated from your latest image and video "
                "analyses in this session.", "chart", "Insights")

    image_result: Optional[ImageAnalysisResult] = st.session_state.get("image_result")
    video_result: Optional[VideoAnalysisResult] = st.session_state.get("video_result")

    if image_result is None and video_result is None:
        empty_state("No analytics yet",
                    "Run an image analysis or process a video first. Charts appear here automatically, "
                    "built from real detection data.", "chart")
        st.write("")
        _, c1, c2, _ = st.columns([1, 1, 1, 1])
        c1.button("Go to Image Analysis", icon=":material/image_search:", type="primary",
                  on_click=go_to, args=("image",), width="stretch", key="an_go_img")
        c2.button("Go to Video Tracking", icon=":material/videocam:", on_click=go_to, args=("video",),
                  width="stretch", key="an_go_vid")
        return

    labels = []
    if image_result is not None:
        labels.append(":material/image: Image analytics")
    if video_result is not None:
        labels.append(":material/videocam: Video analytics")
    labels.append(":material/history: Session history")
    tabs = st.tabs(labels)
    i = 0
    if image_result is not None:
        with tabs[i]:
            _image_section(image_result)
        i += 1
    if video_result is not None:
        with tabs[i]:
            _video_section(video_result)
        i += 1
    with tabs[i]:
        _history_section()


# ---------------------------------------------------------------------------
def _image_section(result: ImageAnalysisResult) -> None:
    meta = st.session_state.get("image_meta", {})
    w, h = result.size
    stat_grid([
        stat_card("Total objects detected", result.object_count, "target", "indigo"),
        stat_card("Selected colour", result.color_name, "palette", "violet", small=True),
        stat_card("Image dimensions", f"{w} × {h}", "ruler", "sky", small=True),
        stat_card("Processing time", f"{result.processing_ms:.1f} ms", "clock", "green"),
        stat_card("Detection percentage", f"{result.coverage_percent:.2f}%", "percent", "amber",
                  "Pixels matching the target colour"),
    ], min_width=170)

    run_key = f"{id(result)}-{result.processing_ms}"
    dist = _distribution(run_key, result.original)
    # Map custom colours to no family highlight
    highlight = result.color_name if result.color_name in dist else None

    section_title("Colour distribution", "Share of all pixels per colour family (HSV classification)")
    c1, c2 = st.columns([1, 1.25], gap="large")
    with c1:
        with st.container(key="card_an_donut"):
            card_title("Composition", "palette", meta.get("name", ""))
            show_figure(analytics.distribution_donut(dist, highlight), key="an_donut")
    with c2:
        with st.container(key="card_an_bar"):
            card_title("Colour families", "chart", "selected colour outlined")
            show_figure(analytics.distribution_bar(dist, highlight), key="an_bar")

    section_title("Object detection", "Area of each detected object and hue spectrum")
    c1, c2 = st.columns([1, 1.25], gap="large")
    with c1:
        with st.container(key="card_an_objects"):
            card_title("Objects by area", "box", f"{result.object_count} object(s)")
            if result.objects:
                show_figure(analytics.objects_area_bar(result.objects, meta.get("hex", "#6366F1")),
                            key="an_area")
            else:
                st.caption("No objects were detected in this image, so there is nothing to chart.")
    with c2:
        with st.container(key="card_an_hue"):
            card_title("Hue spectrum (Matplotlib)", "sparkles", "shaded band = selected HSV range")
            fig = analytics.hue_spectrum_figure(result.original, result.ranges)
            st.pyplot(fig, width="stretch")
            plt.close(fig)

    section_title("Visual comparison", "Original → binary mask → processed result")
    c1, c2, c3 = st.columns(3)
    c1.image(bgr_to_rgb(result.original), caption="Original image", width="stretch")
    c2.image(result.clean_mask, caption="Binary mask", width="stretch")
    c3.image(bgr_to_rgb(result.annotated), caption="Processed image", width="stretch")


# ---------------------------------------------------------------------------
def _video_section(result: VideoAnalysisResult) -> None:
    meta = st.session_state.get("video_meta", {})
    stat_grid([
        stat_card("Frames processed", f"{result.frames_processed:,}", "frames", "indigo"),
        stat_card("Frames with detections", f"{result.frames_with_detections:,}", "scan", "sky"),
        stat_card("Detection frequency", f"{result.detection_frequency:.1f}%", "percent", "violet"),
        stat_card("Avg processing / frame", f"{result.avg_frame_ms:.2f} ms", "clock", "green"),
        stat_card("Unique track IDs", result.unique_tracks, "route", "amber",
                  f"{result.total_detections:,} detections total"),
    ], min_width=170)

    section_title("Detections over time", f"{result.color_name} · {meta.get('name', '')}")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        with st.container(key="card_an_opf"):
            card_title("Objects per frame", "activity")
            show_figure(analytics.objects_per_frame(result.per_frame), key="an_opf")
    with c2:
        with st.container(key="card_an_time"):
            card_title("Processing time per frame", "clock")
            show_figure(analytics.processing_time_chart(result.per_frame), key="an_time")

    section_title("Tracking", "Centroid trajectories and how long each ID was tracked")
    c1, c2 = st.columns([1.3, 1], gap="large")
    with c1:
        with st.container(key="card_an_traj"):
            card_title("Centroid trajectories", "route", "○ start · ● end")
            if result.paths:
                w, h = result.output_size
                show_figure(analytics.trajectory_chart(result.paths, w, h), key="an_traj")
            else:
                st.caption("No tracks were created.")
    with c2:
        with st.container(key="card_an_life"):
            card_title("Track lifetimes", "frames")
            if result.tracks:
                show_figure(analytics.track_lifetime_chart(result.tracks), key="an_life")
            else:
                st.caption("No tracks were created.")
    if result.tracks:
        st.dataframe(result.tracks, hide_index=True, width="stretch")


# ---------------------------------------------------------------------------
def _history_section() -> None:
    images = st.session_state.image_history
    videos = st.session_state.video_history
    if images:
        section_title("Image analysis runs", f"{len(images)} run(s) this session")
        show_figure(analytics.history_bar(images), key="an_hist")
        st.dataframe([{"Run": i + 1, "Image": r["image"], "Colour": r["color"], "Objects": r["objects"],
                       "Coverage (%)": r["coverage"], "Time (ms)": r["ms"]} for i, r in enumerate(images)],
                     hide_index=True, width="stretch")
    if videos:
        section_title("Video processing runs", f"{len(videos)} run(s) this session")
        st.dataframe([{"Run": i + 1, "Video": r["video"], "Colour": r["color"], "Frames": r["frames"],
                       "Frames with detections": r["with_detections"], "Track IDs": r["tracks"],
                       "Avg ms/frame": r["avg_ms"]} for i, r in enumerate(videos)],
                     hide_index=True, width="stretch")
    if not images and not videos:
        st.caption("No runs recorded yet.")
