"""
Session-state and temporary-file management.

Streamlit re-runs the script on every interaction; st.session_state keeps
values (current page, results, statistics) between those re-runs.
"""

from __future__ import annotations

import os
import shutil
import time
import uuid

import streamlit as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(ROOT, "outputs")
SESSION_ROOT = os.path.join(OUTPUT_DIR, "sessions")
SAMPLE_IMAGE_DIR = os.path.join(ROOT, "assets", "sample_images")
SAMPLE_VIDEO_DIR = os.path.join(ROOT, "assets", "sample_videos")

PAGES = {
    "overview": ("Overview", ":material/space_dashboard:"),
    "image": ("Image Analysis", ":material/image_search:"),
    "video": ("Video Tracking", ":material/videocam:"),
    "analytics": ("Analytics & Insights", ":material/monitoring:"),
    "about": ("About Project", ":material/menu_book:"),
}

# Session folders older than this are deleted automatically.
MAX_SESSION_AGE_HOURS = 12


def init_state() -> None:
    """Create every session-state key the app relies on (once per session)."""
    defaults = {
        "page": "overview",
        "session_id": uuid.uuid4().hex[:12],
        "stats": {"images": 0, "videos": 0, "objects": 0, "frames": 0},
        "image_result": None,
        "image_history": [],
        "image_bytes": None,
        "image_name": None,
        "image_file_id": None,
        "auto_analyze": False,
        "video_path": None,
        "video_name": None,
        "video_file_id": None,
        "video_info": None,
        "video_preview": None,
        "video_result": None,
        "video_history": [],
        "auto_process_video": False,
    }
    first_run = "session_id" not in st.session_state
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if first_run:
        cleanup_old_sessions()
        # Support deep links such as ?page=video
        requested = st.query_params.get("page")
        if requested in PAGES:
            st.session_state.page = requested


def go_to(page: str) -> None:
    """Navigation callback used by sidebar and in-page buttons."""
    if page in PAGES:
        st.session_state.page = page
        st.query_params["page"] = page


def session_dir() -> str:
    """Per-session folder for uploads and generated videos."""
    path = os.path.join(SESSION_ROOT, st.session_state.session_id)
    os.makedirs(path, exist_ok=True)
    return path


def remove_file(path) -> None:
    """Delete a temporary file, ignoring errors (it may already be gone)."""
    if path and os.path.isfile(path) and os.path.abspath(path).startswith(os.path.abspath(SESSION_ROOT)):
        try:
            os.remove(path)
        except OSError:
            pass


def cleanup_old_sessions() -> None:
    """Delete session folders that have not been modified for a while."""
    if not os.path.isdir(SESSION_ROOT):
        return
    cutoff = time.time() - MAX_SESSION_AGE_HOURS * 3600
    for name in os.listdir(SESSION_ROOT):
        folder = os.path.join(SESSION_ROOT, name)
        try:
            if os.path.isdir(folder) and os.path.getmtime(folder) < cutoff:
                shutil.rmtree(folder, ignore_errors=True)
        except OSError:
            pass


def list_samples(folder: str, extensions) -> list:
    if not os.path.isdir(folder):
        return []
    return sorted(f for f in os.listdir(folder) if f.lower().endswith(tuple(extensions)))
