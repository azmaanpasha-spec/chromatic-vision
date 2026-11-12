"""Video Tracking Studio: upload a video, detect a colour and track objects."""

from __future__ import annotations

import csv
import io
import os
from typing import Optional

import streamlit as st

from components.color_picker import color_selector
from components.state import SAMPLE_VIDEO_DIR, list_samples, remove_file, session_dir
from components.ui_components import (card_title, chips, empty_state, page_header, section_title,
                                      show_figure, stat_card, stat_grid)
from modules import analytics
from modules.image_processing import bgr_to_rgb
from modules.video_processing import (VideoAnalysisResult, get_video_info, make_preview, process_video,
                                      read_frame)

SOURCES = ["Upload video", "Sample video"]
VIDEO_TYPES = ["mp4", "avi", "mov"]


# ---------------------------------------------------------------------------
# Input handling
# ---------------------------------------------------------------------------
def _clear_video() -> None:
    """Forget the current input video and delete its temporary files."""
    ss = st.session_state
    if ss.video_path and ss.video_path.startswith(session_dir()):
        remove_file(ss.video_path)
    remove_file(ss.video_preview)
    ss.video_path = ss.video_preview = ss.video_info = ss.video_name = None
    ss.video_sig = None
    ss.video_thumb = None


def _load_video(path: str, name: str, signature: str) -> None:
    """Validate a video, read its metadata and build a preview clip."""
    ss = st.session_state
    _clear_video()
    try:
        info = get_video_info(path)
    except ValueError as exc:
        if path.startswith(session_dir()):
            remove_file(path)
        ss.video_error = str(exc)
        ss.video_sig = signature  # remember so we do not retry the same broken file every rerun
        return
    ss.video_error = None
    ss.video_path, ss.video_name, ss.video_info, ss.video_sig = path, name, info, signature
    ss.video_thumb = read_frame(path, 0)
    with st.spinner("Preparing preview..."):
        ss.video_preview = make_preview(path, session_dir())
    ss.video_result = None


def _handle_input() -> None:
    ss = st.session_state
    if ss.get("vid_src_mode") not in SOURCES:
        ss.vid_src_mode = SOURCES[0]
    mode = st.segmented_control("Video source", SOURCES, key="vid_src_mode", required=True,
                                label_visibility="collapsed", width="stretch")

    if mode == "Upload video":
        uploaded = st.file_uploader("Drag and drop a video (MP4, AVI, MOV)", type=VIDEO_TYPES,
                                    key="vid_uploader")
        if uploaded is None:
            ss.video_error = None
            if (ss.get("video_sig") or "").startswith("upload:"):
                _clear_video()
                ss.video_result = None
            return
        signature = f"upload:{uploaded.file_id}"
        if signature != ss.get("video_sig"):
            data = uploaded.getvalue()
            if not data:
                ss.video_error = "The uploaded video file is empty."
                ss.video_sig = signature
                _clear_video_keep_error(signature)
                return
            ext = os.path.splitext(uploaded.name)[1].lower() or ".mp4"
            path = os.path.join(session_dir(), f"input_{uploaded.file_id[:8]}{ext}")
            with open(path, "wb") as fh:
                fh.write(data)
            _load_video(path, uploaded.name, signature)
    else:
        samples = list_samples(SAMPLE_VIDEO_DIR, tuple("." + t for t in VIDEO_TYPES))
        if not samples:
            st.warning("No sample videos found in assets/sample_videos. "
                       "Run `python scripts/generate_samples.py` to create them.")
            return
        if ss.get("vid_sample") not in samples:
            ss.vid_sample = samples[0]
        name = st.selectbox("Sample video", samples, key="vid_sample")
        signature = f"sample:{name}"
        if signature != ss.get("video_sig"):
            _load_video(os.path.join(SAMPLE_VIDEO_DIR, name), name, signature)


def _clear_video_keep_error(signature: str) -> None:
    err = st.session_state.video_error
    _clear_video()
    st.session_state.video_error = err
    st.session_state.video_sig = signature


# ---------------------------------------------------------------------------
# Processing
# ---------------------------------------------------------------------------
def _process(color, kernel, min_area, max_distance, max_disappeared, max_width, max_frames, trails,
             progress_area) -> None:
    ss = st.session_state
    with progress_area.container(key="card_vid_progress"):
        card_title("Processing", "activity", "frame-by-frame")
        bar = st.progress(0.0, text="Starting...")
        live = st.empty()

    def on_progress(done: int, total: int, frame) -> None:
        bar.progress(min(1.0, done / max(total, 1)), text=f"Processing frame {done:,} of {total:,}")
        if frame is not None:
            live.image(bgr_to_rgb(frame), caption="Live preview", width="stretch")

    try:
        result = process_video(ss.video_path, session_dir(), color.ranges, color.name, kernel_size=kernel,
                               min_area=min_area, max_distance=max_distance, max_disappeared=max_disappeared,
                               max_width=max_width, max_frames=max_frames or None, draw_trails=trails,
                               progress=on_progress)
    except (ValueError, RuntimeError) as exc:
        progress_area.error(f"**Processing failed.** {exc}", icon=":material/error:")
        return
    progress_area.empty()

    # Replace any previous output files
    old: Optional[VideoAnalysisResult] = ss.get("video_result")
    if old is not None:
        remove_file(old.webm_path)
        remove_file(old.mp4_path)

    ss.video_result = result
    ss.video_meta = {"name": ss.video_name, "hex": color.hex}
    ss.stats["videos"] += 1
    ss.stats["frames"] += result.frames_processed
    ss.stats["objects"] += result.unique_tracks
    ss.video_history.append({
        "video": ss.video_name, "color": color.name, "frames": result.frames_processed,
        "with_detections": result.frames_with_detections, "tracks": result.unique_tracks,
        "avg_ms": round(result.avg_frame_ms, 2),
    })


def per_frame_csv(result: VideoAnalysisResult) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(result.per_frame[0].keys()))
    writer.writeheader()
    writer.writerows(result.per_frame)
    return buffer.getvalue().encode("utf-8")


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
def render_video_studio() -> None:
    ss = st.session_state
    page_header("Video Tracking Studio",
                "Process a video frame by frame, detect objects of a target colour and follow them with "
                "centroid-based tracking.", "video", "Workspace · Video")

    left, right = st.columns([1, 1.7], gap="large")
    with left:
        with st.container(key="card_vid_input"):
            card_title("Input video", "upload", "MP4 · AVI · MOV")
            _handle_input()
            if ss.get("video_error"):
                st.error(f"**Invalid video.** {ss.video_error}", icon=":material/error:")

        with st.container(key="card_vid_color"):
            card_title("Target colour", "palette")
            color = color_selector("vid")

        with st.container(key="card_vid_params"):
            card_title("Tracking parameters", "route")
            min_area = st.slider("Minimum object area (px)", 20, 3000, 250, step=10, key="vid_min_area")
            max_distance = st.slider("Max match distance (px)", 10, 300, 80, step=5, key="vid_max_dist",
                                     help="A detection further than this from a track starts a new ID.")
            max_disappeared = st.slider("Frames to keep a lost ID", 0, 60, 15, key="vid_max_dis",
                                        help="How long a track survives without a matching detection.")
            kernel = st.select_slider("Morphology kernel", options=[3, 5, 7, 9], value=5, key="vid_kernel")
            max_width = st.selectbox("Processing width", [640, 960, 1280, 0], index=1, key="vid_width",
                                     format_func=lambda w: "Original" if w == 0 else f"{w} px (max)",
                                     help="Large videos are scaled down to keep processing fast.")
            max_frames = st.number_input("Frame limit (0 = all frames)", 0, 100000, 0, step=50, key="vid_limit")
            trails = st.toggle("Draw motion trails", value=True, key="vid_trails")
            clicked = st.button("Process Video", type="primary", icon=":material/play_arrow:", width="stretch",
                                disabled=ss.video_path is None, key="vid_process")

    with right:
        info = ss.video_info
        if info is None:
            empty_state("No video loaded",
                        "Upload an MP4, AVI or MOV file, or choose “Sample video” to try the bundled "
                        "tracking demo.", "video")
        else:
            stat_grid([
                stat_card("FPS", f"{info.fps:.2f}", "gauge", "indigo"),
                stat_card("Total frames", f"{info.frame_count:,}", "frames", "sky"),
                stat_card("Resolution", info.resolution, "ruler", "violet", small=True),
                stat_card("Duration", f"{info.duration:.2f} s", "clock", "green"),
            ], min_width=120)
            st.write("")
            with st.container(key="card_vid_preview"):
                card_title("Video preview", "film", ss.video_name or "")
                if ss.video_preview:
                    st.video(ss.video_preview, format="video/webm")
                    st.caption("Preview shows up to the first 12 seconds (re-encoded for the browser).")
                elif ss.get("video_thumb") is not None:
                    st.image(bgr_to_rgb(ss.video_thumb), caption="First frame", width="stretch")
        progress_area = st.empty()

    if ss.video_path and (clicked or ss.get("auto_process_video")):
        ss.auto_process_video = False
        _process(color, kernel, min_area, max_distance, max_disappeared, max_width, max_frames, trails,
                 progress_area)
    elif ss.video_path is None:
        ss.auto_process_video = False

    result: Optional[VideoAnalysisResult] = ss.get("video_result")
    if result is not None and ss.video_path is not None:
        _render_result(result)


def _render_result(result: VideoAnalysisResult) -> None:
    section_title("Tracking results", f"{result.color_name} · {st.session_state.video_meta['name']}")
    stat_grid([
        stat_card("Frames processed", f"{result.frames_processed:,}", "frames", "indigo",
                  f"{result.total_seconds:.1f} s total"),
        stat_card("Frames with detections", f"{result.frames_with_detections:,}", "scan", "sky"),
        stat_card("Detection frequency", f"{result.detection_frequency:.1f}%", "percent", "violet"),
        stat_card("Avg time / frame", f"{result.avg_frame_ms:.1f} ms", "clock", "green",
                  f"≈ {1000 / result.avg_frame_ms:.0f} FPS throughput" if result.avg_frame_ms else ""),
        stat_card("Unique track IDs", result.unique_tracks, "route", "amber",
                  f"Max {result.max_objects_in_frame} in one frame"),
    ], min_width=170)

    if result.frames_with_detections == 0:
        st.info(f"No **{result.color_name.lower()}** objects were detected in any frame. The output video "
                "is still generated; try another colour or relax the thresholds.", icon=":material/search_off:")

    st.write("")
    v1, v2 = st.columns([1.5, 1], gap="large")
    with v1:
        with st.container(key="card_vid_output"):
            card_title("Processed video", "film", f"{result.output_size[0]}×{result.output_size[1]}")
            st.video(result.webm_path, format="video/webm")
    with v2:
        with st.container(key="card_vid_chart"):
            card_title("Objects per frame", "activity")
            show_figure(analytics.objects_per_frame(result.per_frame), key="vid_opf")
            chips([("Full analytics on the Analytics & Insights page", "")])

    section_title("Downloads", "Processed video and per-frame data")
    c1, c2, c3 = st.columns(3)
    base = os.path.splitext(st.session_state.video_meta["name"] or "video")[0]
    tag = result.color_name.lower()
    with open(result.webm_path, "rb") as fh:
        c1.download_button("Processed video (WebM)", fh.read(), f"{base}_{tag}_tracked.webm", "video/webm",
                           icon=":material/download:", width="stretch", on_click="ignore", key="dl_webm")
    if result.mp4_path and os.path.exists(result.mp4_path):
        with open(result.mp4_path, "rb") as fh:
            c2.download_button("Processed video (MP4)", fh.read(), f"{base}_{tag}_tracked.mp4", "video/mp4",
                               icon=":material/download:", width="stretch", on_click="ignore", key="dl_mp4")
    c3.download_button("Per-frame data (CSV)", per_frame_csv(result), f"{base}_{tag}_frames.csv", "text/csv",
                       icon=":material/table_view:", width="stretch", on_click="ignore", key="dl_fcsv")
    st.caption("WebM (VP8) plays in any modern browser and VLC. MP4 uses the MPEG-4 Part 2 codec and opens "
               "in VLC and Windows Media Player.")
