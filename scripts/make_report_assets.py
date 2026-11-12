"""
Generate sample outputs and report figures from the REAL pipeline.

    python scripts/make_report_assets.py

Creates
    outputs/samples/            processed image, mask, segmented image, tracked videos, CSV
    report/figures/             architecture + workflow diagrams, pipeline stages,
                                tracking frame strip, measured results (JSON)
"""

from __future__ import annotations

import csv
import json
import os
import shutil
import sys

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from modules.color_ranges import COLOR_PRESETS  # noqa: E402
from modules.image_processing import analyze_image, bgr_to_rgb, load_image_from_path  # noqa: E402
from modules.video_processing import process_video  # noqa: E402

SAMPLES_OUT = os.path.join(ROOT, "outputs", "samples")
FIG = os.path.join(ROOT, "report", "figures")
BG, CARD, TEXT, MUTED, LAYER = "#0B1020", "#151D30", "#F8FAFC", "#94A3B8", "#10162B"
INDIGO, SKY, VIOLET, GREEN = "#6366F1", "#38BDF8", "#A78BFA", "#22C55E"


def box(ax, x, y, w, h, title, sub="", color=INDIGO, fs=10.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.025",
                                fc=CARD, ec=color, lw=1.6))
    ax.text(x + w / 2, y + h * (0.62 if sub else 0.5), title, ha="center", va="center",
            color=TEXT, fontsize=fs, fontweight="bold")
    if sub:
        ax.text(x + w / 2, y + h * 0.3, sub, ha="center", va="center", color=MUTED, fontsize=fs - 2.5)


def arrow(ax, p1, p2, color="#64748B"):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=14, color=color, lw=1.4))


def architecture_diagram():
    fig, ax = plt.subplots(figsize=(12, 7), dpi=150)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.5, 0.965, "Chromatic Vision - System Architecture", ha="center", color=TEXT, fontsize=15,
            fontweight="bold")
    layers = [
        (0.70, "PRESENTATION LAYER (Streamlit)", SKY,
         [("app.py", "routing, page config"), ("components/", "sidebar, colour picker, UI kit"),
          ("views/", "5 pages"), ("styles/main.css", "dark theme")]),
        (0.40, "PROCESSING LAYER (modules/)", VIOLET,
         [("color_ranges.py", "HSV presets"), ("image_processing.py", "mask, morphology, contours"),
          ("video_processing.py", "frame loop, encoding"), ("object_tracking.py", "centroid tracker"),
          ("analytics.py", "distributions, charts")]),
        (0.10, "FOUNDATION", GREEN,
         [("OpenCV + NumPy", "vision, arrays"), ("Plotly + Matplotlib", "visualisation"),
          ("st.session_state", "results, statistics"), ("outputs/sessions/", "temporary files")]),
    ]
    for y, title, color, items in layers:
        ax.add_patch(FancyBboxPatch((0.03, y - 0.02), 0.94, 0.23, boxstyle="round,pad=0.005,rounding_size=0.02",
                                    fc=LAYER, ec=color, lw=1.2, alpha=0.95))
        ax.text(0.05, y + 0.185, title, color=color, fontsize=10, fontweight="bold")
        n = len(items)
        w = (0.90 - 0.02 * (n - 1)) / n
        for i, (t, s) in enumerate(items):
            box(ax, 0.05 + i * (w + 0.02), y, w, 0.15, t, s, color, fs=10.5 if n < 5 else 9)
    for y in (0.68, 0.38):
        arrow(ax, (0.5, y), (0.5, y - 0.07))
        arrow(ax, (0.53, y - 0.07), (0.53, y))
    ax.text(0.56, 0.645, "user input (files, colour, parameters)  /  results", color=MUTED, fontsize=8, va="center")
    ax.text(0.56, 0.345, "library calls  /  arrays, encoded media", color=MUTED, fontsize=8, va="center")
    fig.savefig(os.path.join(FIG, "fig_architecture.png"), facecolor=BG, bbox_inches="tight")
    plt.close(fig)


def workflow_diagram():
    steps = [("Input", "image / video"), ("BGR → HSV", "cv2.cvtColor"), ("Threshold", "cv2.inRange"),
             ("Morphology", "open + close"), ("Contours", "findContours"), ("Box + centroid", "boundingRect\nmoments"),
             ("Tracking", "CentroidTracker\n(video only)"), ("Output", "media, charts, CSV")]
    fig, ax = plt.subplots(figsize=(13, 4.2), dpi=150)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.5, 0.93, "Processing Workflow", ha="center", color=TEXT, fontsize=14, fontweight="bold")
    n = len(steps)
    w, gap = 0.098, (1 - 0.04 - 0.098 * 8) / 7
    colors = [SKY, INDIGO, INDIGO, VIOLET, VIOLET, VIOLET, "#F59E0B", GREEN]
    for i, (t, s) in enumerate(steps):
        x = 0.02 + i * (w + gap)
        box(ax, x, 0.35, w, 0.36, t, s, colors[i], fs=9.5)
        ax.text(x + w / 2, 0.77, f"{i + 1:02d}", ha="center", color=colors[i], fontsize=9, fontweight="bold")
        if i < n - 1:
            arrow(ax, (x + w + 0.003, 0.53), (x + w + gap - 0.003, 0.53))
    ax.annotate("", xy=(0.02 + w / 2, 0.3), xytext=(0.02 + 6 * (w + gap) + w / 2, 0.3),
                arrowprops=dict(arrowstyle="-|>", color="#64748B", lw=1.2, connectionstyle="arc3,rad=-0.25"))
    ax.text(0.40, 0.08, "for video: repeat steps 2-7 for every frame, writing each annotated frame to the output",
            ha="center", color=MUTED, fontsize=9)
    fig.savefig(os.path.join(FIG, "fig_workflow.png"), facecolor=BG, bbox_inches="tight")
    plt.close(fig)


def pipeline_figure(result):
    panels = [("(a) Original", bgr_to_rgb(result.original), None),
              ("(b) Raw mask - cv2.inRange", result.raw_mask, "gray"),
              ("(c) Erosion", result.stages["Eroded"], "gray"),
              ("(d) Dilation", result.stages["Dilated"], "gray"),
              ("(e) Opening + closing (final mask)", result.clean_mask, "gray"),
              ("(f) Detected objects", bgr_to_rgb(result.annotated), None)]
    fig, axes = plt.subplots(2, 3, figsize=(13, 6.2), dpi=150)
    fig.patch.set_facecolor("white")
    for ax, (title, img, cmap) in zip(axes.flat, panels):
        ax.imshow(img, cmap=cmap)
        ax.set_title(title, fontsize=10)
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_pipeline_stages.png"), bbox_inches="tight")
    plt.close(fig)


def tracking_strip(video_path):
    cap = cv2.VideoCapture(video_path)
    wanted = [0, 60, 100, 150, 199]
    frames, idx = {}, 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        if idx in wanted:
            frames[idx] = f
        idx += 1
    cap.release()
    fig, axes = plt.subplots(1, len(frames), figsize=(16, 2.6), dpi=150)
    for ax, (i, f) in zip(axes, sorted(frames.items())):
        ax.imshow(bgr_to_rgb(f))
        ax.set_title(f"Frame {i + 1}", fontsize=9)
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_tracking_frames.png"), bbox_inches="tight")
    plt.close(fig)


def main():
    os.makedirs(SAMPLES_OUT, exist_ok=True)
    os.makedirs(FIG, exist_ok=True)
    architecture_diagram()
    workflow_diagram()

    measured = {"images": [], "videos": []}
    img = load_image_from_path(os.path.join(ROOT, "assets", "sample_images", "shapes_scene.png"))
    for color in COLOR_PRESETS:
        spec = COLOR_PRESETS[color]
        r = analyze_image(img, spec.ranges, color, spec.bgr)
        measured["images"].append({"image": "shapes_scene.png", "color": color, "objects": r.object_count,
                                   "coverage": round(r.coverage_percent, 2), "ms": round(r.processing_ms, 1)})
        if color == "Red":
            red = r
    cv2.imwrite(os.path.join(SAMPLES_OUT, "shapes_scene_red_detected.png"), red.annotated)
    cv2.imwrite(os.path.join(SAMPLES_OUT, "shapes_scene_red_mask.png"), red.clean_mask)
    cv2.imwrite(os.path.join(SAMPLES_OUT, "shapes_scene_red_segmented.png"), red.segmented)
    pipeline_figure(red)

    img2 = load_image_from_path(os.path.join(ROOT, "assets", "sample_images", "ball_collection.jpg"))
    for color in ("Red", "Blue", "Green"):
        spec = COLOR_PRESETS[color]
        r = analyze_image(img2, spec.ranges, color, spec.bgr)
        measured["images"].append({"image": "ball_collection.jpg", "color": color, "objects": r.object_count,
                                   "coverage": round(r.coverage_percent, 2), "ms": round(r.processing_ms, 1)})

    tmp = os.path.join(ROOT, "outputs", "_tmp_report")
    os.makedirs(tmp, exist_ok=True)
    for name, color in [("moving_objects.mp4", "Red"), ("moving_objects.mp4", "Blue"),
                        ("moving_objects.mp4", "Purple"), ("orbiting_ball.avi", "Orange")]:
        spec = COLOR_PRESETS[color]
        v = process_video(os.path.join(ROOT, "assets", "sample_videos", name), tmp, spec.ranges, color)
        measured["videos"].append({"video": name, "color": color, "frames": v.frames_processed,
                                   "with_detections": v.frames_with_detections,
                                   "frequency": round(v.detection_frequency, 1), "tracks": v.unique_tracks,
                                   "avg_ms": round(v.avg_frame_ms, 2), "tracks_detail": v.tracks})
        if name == "moving_objects.mp4" and color == "Red":
            shutil.copy(v.webm_path, os.path.join(SAMPLES_OUT, "moving_objects_red_tracked.webm"))
            shutil.copy(v.mp4_path, os.path.join(SAMPLES_OUT, "moving_objects_red_tracked.mp4"))
            with open(os.path.join(SAMPLES_OUT, "moving_objects_red_frames.csv"), "w", newline="",
                      encoding="utf-8") as fh:
                wr = csv.DictWriter(fh, fieldnames=list(v.per_frame[0].keys()))
                wr.writeheader()
                wr.writerows(v.per_frame)
            tracking_strip(v.mp4_path)
        for p in (v.webm_path, v.mp4_path):
            if p and os.path.exists(p):
                os.remove(p)
    os.rmdir(tmp)

    with open(os.path.join(FIG, "measured_results.json"), "w", encoding="utf-8") as fh:
        json.dump(measured, fh, indent=2)
    print(json.dumps(measured, indent=1))


if __name__ == "__main__":
    main()
