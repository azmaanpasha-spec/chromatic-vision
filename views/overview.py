"""Overview dashboard (home page)."""

from __future__ import annotations

import streamlit as st

from components.state import go_to
from components.ui_components import (feature_card, feature_grid, render, section_title, stat_card,
                                      stat_grid)


def _start_image_demo() -> None:
    st.session_state.img_src_mode = "Sample image"
    st.session_state.img_sample = "shapes_scene.png"
    st.session_state.img_color = "Red"
    st.session_state.auto_analyze = True
    go_to("image")


def _start_video_demo() -> None:
    st.session_state.vid_src_mode = "Sample video"
    st.session_state.vid_sample = "moving_objects.mp4"
    st.session_state.vid_color = "Red"
    st.session_state.auto_process_video = True
    go_to("video")


def render_overview() -> None:
    render(
        '<div class="cv-hero"><div class="cv-hero-spectrum"></div><div class="cv-hero-spectrum inner"></div>'
        '<span class="cv-hero-badge"><span class="dot"></span>Image &amp; Video Analytics · Computer Vision</span>'
        '<h1>Chromatic Vision</h1><div class="tagline">See Beyond Colors. Understand Every Frame.</div>'
        '<p class="sub">An intelligent image and video analytics platform that identifies colors, detects '
        'objects, and tracks their movement using computer vision.</p></div>'
    )
    c1, c2, _ = st.columns([1, 1, 2.2])
    c1.button("Start Image Analysis", icon=":material/image_search:", type="primary",
              on_click=go_to, args=("image",), width="stretch", key="hero_image")
    c2.button("Start Video Tracking", icon=":material/videocam:", type="secondary",
              on_click=go_to, args=("video",), width="stretch", key="hero_video")

    s = st.session_state.stats
    section_title("Session statistics", "Live values from your analyses in this browser session")
    stat_grid([
        stat_card("Total Images Analysed", s["images"], "image", "indigo", "Analyze runs on images"),
        stat_card("Total Videos Processed", s["videos"], "video", "sky", "Completed tracking jobs"),
        stat_card("Total Objects Detected", f'{s["objects"]:,}', "target", "violet",
                  "Image objects + unique video track IDs"),
        stat_card("Total Frames Analysed", f'{s["frames"]:,}', "frames", "green", "Video frames processed"),
    ])
    if s["images"] == 0 and s["videos"] == 0:
        st.caption("No analyses yet. Statistics start at zero and update as you process images and videos.")

    section_title("Quick demo", "Explore instantly with the bundled sample files")
    d1, d2 = st.columns(2)
    with d1.container(key="card_demo_img"):
        render('<div class="cv-card-title"><b>Sample image demo</b><small>shapes_scene.png</small></div>'
               '<p style="font-size:.88rem;color:#94A3B8;margin:0 0 12px 0">Loads a scene with 15 coloured '
               'shapes and runs red detection immediately - mask, contours and bounding boxes included.</p>')
        st.button("Try Sample Image Demo", icon=":material/play_circle:", key="demo_img",
                  on_click=_start_image_demo, width="stretch")
    with d2.container(key="card_demo_vid"):
        render('<div class="cv-card-title"><b>Sample video demo</b><small>moving_objects.mp4</small></div>'
               '<p style="font-size:.88rem;color:#94A3B8;margin:0 0 12px 0">Tracks two red balls across 200 '
               'frames, including a short occlusion, with centroid-based ID assignment.</p>')
        st.button("Try Sample Video Demo", icon=":material/play_circle:", key="demo_vid",
                  on_click=_start_video_demo, width="stretch")

    section_title("Capabilities", "What the platform does under the hood")
    feature_grid([
        feature_card("Intelligent Color Detection",
                     "Six tuned colour presets plus a custom HSV range builder. Red uses a dual hue range "
                     "because it wraps around the hue circle.", "palette", "indigo"),
        feature_card("HSV Image Segmentation",
                     "Images are converted from BGR to HSV and thresholded with cv2.inRange() to produce a "
                     "clean binary mask of the target colour.", "layers", "sky"),
        feature_card("Object Identification",
                     "Morphological opening and closing remove noise, then contours give each object a "
                     "bounding box, area and centroid.", "scan", "violet"),
        feature_card("Real-Time Frame Analysis",
                     "Each video frame is processed one at a time with live progress, so memory use stays "
                     "constant regardless of video length.", "activity", "green"),
        feature_card("Video Object Tracking",
                     "A centroid tracker links detections between frames, keeps IDs through brief "
                     "occlusions and draws motion trails.", "route", "amber"),
        feature_card("Visual Analytics",
                     "Colour distribution, object areas, detections per frame, trajectories and timing - "
                     "all computed from real results.", "chart", "rose"),
    ])
