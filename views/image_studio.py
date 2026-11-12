"""Image Analysis Studio: upload, choose a colour, detect and download."""

from __future__ import annotations

import csv
import io
import os
from typing import Optional, Tuple

import numpy as np
import streamlit as st
from PIL import Image

from components.color_picker import ColorSelection, color_selector
from components.state import SAMPLE_IMAGE_DIR, list_samples
from components.ui_components import (card_title, chips, empty_state, page_header, section_title,
                                      stat_card, stat_grid)
from modules.image_processing import (ImageAnalysisResult, analyze_image, bgr_to_rgb, encode_png,
                                      load_image_from_bytes)

SOURCES = ["Upload image", "Sample image"]


# ---------------------------------------------------------------------------
# Input handling
# ---------------------------------------------------------------------------
def _get_input() -> Tuple[Optional[np.ndarray], Optional[str], Optional[str], int]:
    """Return (image, name, signature, size_bytes) for the current source."""
    if st.session_state.get("img_src_mode") not in SOURCES:
        st.session_state.img_src_mode = SOURCES[0]
    mode = st.segmented_control("Image source", SOURCES, key="img_src_mode", required=True,
                                label_visibility="collapsed", width="stretch")

    data, name, signature = None, None, None
    if mode == "Upload image":
        uploaded = st.file_uploader("Drag and drop an image (JPG, JPEG, PNG)", type=["jpg", "jpeg", "png"],
                                    key="img_uploader")
        if uploaded is not None:
            data, name = uploaded.getvalue(), uploaded.name
            signature = f"upload:{uploaded.file_id}"
    else:
        samples = list_samples(SAMPLE_IMAGE_DIR, (".png", ".jpg", ".jpeg"))
        if not samples:
            st.warning("No sample images found in assets/sample_images. "
                       "Run `python scripts/generate_samples.py` to create them.")
        else:
            if st.session_state.get("img_sample") not in samples:
                st.session_state.img_sample = samples[0]
            name = st.selectbox("Sample image", samples, key="img_sample")
            with open(os.path.join(SAMPLE_IMAGE_DIR, name), "rb") as fh:
                data = fh.read()
            signature = f"sample:{name}"

    if data is None:
        return None, None, None, 0
    st.session_state["_img_format"] = _pil_format(data)  # reads only the file header
    try:
        image = _decode(data)
    except ValueError as exc:
        st.error(f"**Invalid image.** {exc}", icon=":material/error:")
        return None, name, None, len(data)
    return image, name, signature, len(data)


@st.cache_data(show_spinner=False, max_entries=4)
def _decode(data: bytes) -> np.ndarray:
    return load_image_from_bytes(data)


def _pil_format(data: bytes) -> str:
    """File format and colour mode read with Pillow (e.g. 'PNG · RGBA')."""
    try:
        with Image.open(io.BytesIO(data)) as im:
            return f"{im.format} · {im.mode}"
    except Exception:  # noqa: BLE001 - purely informational
        return "unknown format"


def _format_info(_sig) -> str:
    return st.session_state.get("_img_format", "")


# ---------------------------------------------------------------------------
# Running the analysis
# ---------------------------------------------------------------------------
def _run_analysis(image: np.ndarray, name: str, color: ColorSelection, kernel: int,
                  iterations: int, min_area: int) -> None:
    result = analyze_image(image, color.ranges, color.name, color.bgr, kernel, iterations, min_area)
    st.session_state.image_result = result
    st.session_state.image_meta = {"name": name, "hex": color.hex}
    st.session_state.image_downloads = {
        "annotated": encode_png(result.annotated),
        "mask": encode_png(result.clean_mask),
        "segmented": encode_png(result.segmented),
        "csv": _objects_csv(result),
    }
    stats = st.session_state.stats
    stats["images"] += 1
    stats["objects"] += result.object_count
    st.session_state.image_history.append({
        "image": name, "color": color.name, "hex": color.hex, "objects": result.object_count,
        "coverage": round(result.coverage_percent, 2), "ms": round(result.processing_ms, 1),
    })


def _objects_csv(result: ImageAnalysisResult) -> bytes:
    buffer = io.StringIO()
    rows = [o.as_dict() for o in result.objects]
    fields = ["ID", "X", "Y", "Width", "Height", "Area (px)", "Centroid X", "Centroid Y"]
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
def render_image_studio() -> None:
    page_header("Image Analysis Studio",
                "Upload an image, pick a target colour and detect every matching object with HSV "
                "segmentation, morphology and contour analysis.", "image", "Workspace · Image")

    left, right = st.columns([1, 1.7], gap="large")

    with left:
        with st.container(key="card_img_input"):
            card_title("Input image", "upload", "JPG · JPEG · PNG")
            image, name, signature, size_bytes = _get_input()

        # A new image invalidates the previous result
        if signature != st.session_state.get("image_sig"):
            st.session_state.image_sig = signature
            if signature is not None:
                st.session_state.image_result = None

        with st.container(key="card_img_color"):
            card_title("Colour selection", "palette")
            color = color_selector("img")

        with st.container(key="card_img_proc"):
            card_title("Processing controls", "layers")
            kernel = st.select_slider("Morphology kernel size", options=[3, 5, 7, 9, 11], value=5,
                                      key="img_kernel",
                                      help="Size of the structuring element used for erosion/dilation.")
            iterations = st.slider("Morphology iterations", 1, 3, 1, key="img_iter")
            min_area = st.slider("Minimum object area (px)", 0, 5000, 300, step=50, key="img_min_area",
                                 help="Contours smaller than this are treated as noise.")
            clicked = st.button("Analyze Image", type="primary", icon=":material/auto_awesome:",
                                width="stretch", disabled=image is None, key="img_analyze")

    if image is not None and (clicked or st.session_state.get("auto_analyze")):
        st.session_state.auto_analyze = False
        with right:
            with st.spinner("Running colour detection pipeline..."):
                _run_analysis(image, name, color, kernel, iterations, min_area)
    elif image is None:
        st.session_state.auto_analyze = False

    result: Optional[ImageAnalysisResult] = st.session_state.get("image_result")

    with right:
        if image is None:
            empty_state("No image selected",
                        "Drag and drop a JPG or PNG on the left, or switch to “Sample image” to load a "
                        "bundled demo scene.", "image")
        elif result is None:
            with st.container(key="card_img_preview"):
                h, w = image.shape[:2]
                card_title("Image preview", "image", name or "")
                st.image(bgr_to_rgb(image), width="stretch")
                chips([(f"{w} × {h} px", ""), (f"{size_bytes / 1024:,.0f} KB", ""),
                       (_format_info(st.session_state.get("image_sig")), ""), ("Ready to analyse", "ok")])
        else:
            with st.container(key="card_img_compare"):
                card_title("Original vs processed", "grid",
                           f"{result.color_name} · {st.session_state.image_meta['name']}")
                c1, c2 = st.columns(2)
                c1.image(bgr_to_rgb(result.original), caption="Original", width="stretch")
                c2.image(bgr_to_rgb(result.annotated),
                         caption=f"Detected: {result.object_count} {result.color_name.lower()} object(s)",
                         width="stretch")
                kinds = [(f"{result.object_count} object(s) found", "ok" if result.object_count else "warn"),
                         (f"{result.coverage_percent:.2f}% coverage", ""),
                         (f"{result.processing_ms:.1f} ms", "")]
                chips(kinds)

    if result is not None and image is not None:
        _render_results(result)


def _render_results(result: ImageAnalysisResult) -> None:
    section_title("Detection results", "Values computed by the last Analyze run")
    w, h = result.size
    ow, oh = result.original_size
    dims_sub = "Processed at original size" if (w, h) == (ow, oh) else f"Original {ow}×{oh}, scaled for speed"
    stat_grid([
        stat_card("Objects detected", result.object_count, "target", "indigo", f"Target: {result.color_name}"),
        stat_card("Colour coverage", f"{result.coverage_percent:.2f}%", "percent", "sky",
                  "Share of pixels in the clean mask"),
        stat_card("Processing time", f"{result.processing_ms:.1f} ms", "clock", "violet",
                  "HSV → mask → morphology → contours"),
        stat_card("Image dimensions", f"{w} × {h}", "ruler", "green", dims_sub, small=True),
    ])

    if result.object_count == 0:
        st.info(f"No **{result.color_name.lower()}** objects were found. Try another colour, lower the "
                "minimum area, or widen the HSV thresholds under *Fine-tune HSV thresholds*.",
                icon=":material/search_off:")

    st.write("")
    tabs = st.tabs([":material/compare: Comparison", ":material/contrast: Mask & segmentation",
                    ":material/filter_frames: Morphology pipeline", ":material/table: Object table"])
    with tabs[0]:
        c1, c2, c3 = st.columns(3)
        c1.image(bgr_to_rgb(result.original), caption="1 · Original image", width="stretch")
        c2.image(result.clean_mask, caption="2 · Binary mask (clean)", width="stretch")
        c3.image(bgr_to_rgb(result.annotated), caption="3 · Bounding boxes", width="stretch")
    with tabs[1]:
        c1, c2, c3 = st.columns(3)
        c1.image(result.raw_mask, caption="Raw mask from cv2.inRange()", width="stretch")
        c2.image(result.clean_mask, caption="After opening + closing", width="stretch")
        c3.image(bgr_to_rgb(result.segmented), caption="Segmented (bitwise AND)", width="stretch")
    with tabs[2]:
        st.caption(f"Kernel {result.params['kernel_size']}×{result.params['kernel_size']} (ellipse), "
                   f"{result.params['iterations']} iteration(s). Erosion and dilation are shown individually "
                   "for comparison; the pipeline uses opening followed by closing.")
        hsv_vis = result.hsv.copy()
        cols = st.columns(3)
        cols[0].image(bgr_to_rgb(_hsv_preview(hsv_vis)), caption="HSV (hue channel, false colour)",
                      width="stretch")
        cols[1].image(result.raw_mask, caption="Threshold (inRange)", width="stretch")
        cols[2].image(result.stages["Eroded"], caption="Erosion", width="stretch")
        cols = st.columns(3)
        cols[0].image(result.stages["Dilated"], caption="Dilation", width="stretch")
        cols[1].image(result.stages["Opened"], caption="Opening (erode → dilate)", width="stretch")
        cols[2].image(result.stages["Opened + Closed"], caption="Opening → Closing (final)", width="stretch")
    with tabs[3]:
        if result.objects:
            st.dataframe([o.as_dict() for o in result.objects], hide_index=True, width="stretch")
        else:
            st.caption("No objects to list.")

    section_title("Downloads", "PNG images and CSV are generated from this result")
    dl = st.session_state.image_downloads
    base = os.path.splitext(st.session_state.image_meta["name"] or "image")[0]
    tag = result.color_name.lower()
    c1, c2, c3, c4 = st.columns(4)
    c1.download_button("Processed image", dl["annotated"], f"{base}_{tag}_detected.png", "image/png",
                       icon=":material/download:", width="stretch", on_click="ignore", key="dl_img")
    c2.download_button("Binary mask", dl["mask"], f"{base}_{tag}_mask.png", "image/png",
                       icon=":material/download:", width="stretch", on_click="ignore", key="dl_mask")
    c3.download_button("Segmented image", dl["segmented"], f"{base}_{tag}_segmented.png", "image/png",
                       icon=":material/download:", width="stretch", on_click="ignore", key="dl_seg")
    c4.download_button("Objects (CSV)", dl["csv"], f"{base}_{tag}_objects.csv", "text/csv",
                       icon=":material/table_view:", width="stretch", on_click="ignore", key="dl_csv")


def _hsv_preview(hsv: np.ndarray) -> np.ndarray:
    """Visualise the hue channel at full saturation/value (BGR output)."""
    import cv2

    vis = hsv.copy()
    vis[..., 1] = 255
    vis[..., 2] = 255
    return cv2.cvtColor(vis, cv2.COLOR_HSV2BGR)
