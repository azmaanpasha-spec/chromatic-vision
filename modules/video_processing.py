"""
Frame-by-frame video processing with colour detection and centroid tracking.

For every frame:
    BGR frame -> HSV -> cv2.inRange mask -> opening + closing
    -> contours -> bounding boxes + centroids -> CentroidTracker.update()
    -> draw boxes, IDs and motion trails -> write the frame to the output

Frames are read and written one at a time, so memory use stays constant
no matter how long the video is.

Output formats
    * WebM (VP8)        - plays directly in the browser (used for the in-app player)
    * MP4  (MPEG-4 mp4v) - widely supported by desktop players (VLC, Windows)
"""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np

from .color_ranges import HSVRange
from .image_processing import clean_mask, create_mask, draw_label, find_objects, to_hsv
from .object_tracking import CentroidTracker

ProgressCallback = Callable[[int, int, Optional[np.ndarray]], None]

# Distinct colours (BGR) for track IDs so neighbouring objects are easy to tell apart.
TRACK_PALETTE = [
    (241, 102, 99), (248, 189, 56), (250, 139, 167), (94, 197, 34), (11, 158, 245),
    (68, 68, 239), (153, 72, 236), (212, 182, 6), (60, 208, 132), (113, 113, 248),
]


@dataclass
class VideoInfo:
    fps: float
    frame_count: int
    width: int
    height: int

    @property
    def duration(self) -> float:
        return self.frame_count / self.fps if self.fps > 0 else 0.0

    @property
    def resolution(self) -> str:
        return f"{self.width} × {self.height}"


@dataclass
class VideoAnalysisResult:
    webm_path: str
    mp4_path: Optional[str]
    info: VideoInfo
    color_name: str
    frames_processed: int
    frames_with_detections: int
    total_detections: int              # sum of objects over all frames
    unique_tracks: int
    avg_frame_ms: float
    total_seconds: float
    per_frame: List[Dict] = field(default_factory=list)
    tracks: List[Dict] = field(default_factory=list)
    paths: Dict[int, List[Tuple[int, int, int]]] = field(default_factory=dict)
    output_size: Tuple[int, int] = (0, 0)
    params: Dict = field(default_factory=dict)

    @property
    def detection_frequency(self) -> float:
        """Percentage of frames in which at least one object was detected."""
        if self.frames_processed == 0:
            return 0.0
        return 100.0 * self.frames_with_detections / self.frames_processed

    @property
    def max_objects_in_frame(self) -> int:
        return max((row["Objects"] for row in self.per_frame), default=0)


# ---------------------------------------------------------------------------
# Video information
# ---------------------------------------------------------------------------
def get_video_info(path: str) -> VideoInfo:
    """Read FPS, frame count and resolution. Raises ValueError if unreadable."""
    cap = cv2.VideoCapture(path)
    try:
        if not cap.isOpened():
            raise ValueError("The video could not be opened. Please upload a valid MP4, AVI or MOV file.")
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        ok, frame = cap.read()
        if not ok or frame is None:
            raise ValueError("The video contains no readable frames.")
        if width == 0 or height == 0:
            height, width = frame.shape[:2]
        if fps <= 0 or fps > 240:
            fps = 25.0  # sensible default when the container does not report FPS
        if count <= 0:
            # Some containers do not store a frame count - count manually.
            count = 1
            while cap.read()[0]:
                count += 1
        return VideoInfo(fps=float(fps), frame_count=count, width=width, height=height)
    finally:
        cap.release()


def read_frame(path: str, index: int = 0) -> Optional[np.ndarray]:
    """Return one frame (BGR) from the video, or None."""
    cap = cv2.VideoCapture(path)
    try:
        if index > 0:
            cap.set(cv2.CAP_PROP_POS_FRAMES, index)
        ok, frame = cap.read()
        return frame if ok else None
    finally:
        cap.release()


def scaled_size(width: int, height: int, max_width: int) -> Tuple[int, int]:
    """Keep the aspect ratio and make both sides even (required by encoders)."""
    if max_width and width > max_width:
        scale = max_width / float(width)
        width, height = int(width * scale), int(height * scale)
    return width - width % 2, height - height % 2


def open_writer(path: str, fourcc: str, fps: float, size: Tuple[int, int]) -> Optional[cv2.VideoWriter]:
    writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*fourcc), fps, size)
    if not writer.isOpened():
        writer.release()
        return None
    return writer


def make_preview(path: str, output_dir: str, max_seconds: float = 12.0,
                 max_width: int = 640) -> Optional[str]:
    """Create a short browser-playable WebM preview of any input video.

    Browsers cannot play many AVI / MPEG-4 Part 2 files, so we re-encode
    the first few seconds for the preview player.
    """
    try:
        info = get_video_info(path)
    except ValueError:
        return None
    size = scaled_size(info.width, info.height, max_width)
    out_path = os.path.join(output_dir, f"preview_{uuid.uuid4().hex[:8]}.webm")
    writer = open_writer(out_path, "VP80", info.fps, size)
    if writer is None:
        return None
    cap = cv2.VideoCapture(path)
    limit = int(info.fps * max_seconds)
    written = 0
    try:
        while written < limit:
            ok, frame = cap.read()
            if not ok:
                break
            if (frame.shape[1], frame.shape[0]) != size:
                frame = cv2.resize(frame, size, interpolation=cv2.INTER_AREA)
            writer.write(frame)
            written += 1
    finally:
        cap.release()
        writer.release()
    return out_path if written > 0 else None


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------
def track_color(track_id: int) -> Tuple[int, int, int]:
    return TRACK_PALETTE[(track_id - 1) % len(TRACK_PALETTE)]


def draw_hud(frame: np.ndarray, frame_idx: int, total: int, count: int, color_name: str) -> None:
    """Small translucent status panel in the top-left corner."""
    h = frame.shape[0]
    overlay = frame.copy()
    top = h - 30
    cv2.rectangle(overlay, (6, top), (330, h - 6), (32, 16, 11), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(frame, f"{color_name} | Frame {frame_idx + 1}/{total} | Objects: {count}",
                (14, h - 13), font, 0.42, (252, 250, 248), 1, cv2.LINE_AA)


# ---------------------------------------------------------------------------
# Main processing loop
# ---------------------------------------------------------------------------
def process_video(input_path: str, output_dir: str, ranges: Sequence[HSVRange],
                  color_name: str, kernel_size: int = 5, min_area: int = 250,
                  max_distance: float = 80.0, max_disappeared: int = 15,
                  max_width: int = 960, max_frames: Optional[int] = None,
                  draw_trails: bool = True, write_mp4: bool = True,
                  progress: Optional[ProgressCallback] = None,
                  preview_every: int = 15) -> VideoAnalysisResult:
    """Detect and track objects of the target colour in every frame."""
    info = get_video_info(input_path)
    total = info.frame_count if not max_frames else min(info.frame_count, int(max_frames))
    size = scaled_size(info.width, info.height, max_width)
    os.makedirs(output_dir, exist_ok=True)

    stem = f"tracked_{color_name.lower()}_{uuid.uuid4().hex[:8]}"
    webm_path = os.path.join(output_dir, stem + ".webm")
    mp4_path = os.path.join(output_dir, stem + ".mp4") if write_mp4 else None

    webm_writer = open_writer(webm_path, "VP80", info.fps, size)
    if webm_writer is None:
        raise RuntimeError("Could not create the output video (VP8/WebM encoder unavailable).")
    mp4_writer = open_writer(mp4_path, "mp4v", info.fps, size) if mp4_path else None
    if mp4_path and mp4_writer is None:
        mp4_path = None

    tracker = CentroidTracker(max_disappeared=max_disappeared, max_distance=max_distance)
    cap = cv2.VideoCapture(input_path)
    per_frame: List[Dict] = []
    frames_with_det = 0
    total_det = 0
    start_all = time.perf_counter()
    frame_idx = 0

    try:
        while frame_idx < total:
            ok, frame = cap.read()
            if not ok or frame is None:
                break  # end of stream (frame count reported by containers can be approximate)

            t0 = time.perf_counter()
            if (frame.shape[1], frame.shape[0]) != size:
                frame = cv2.resize(frame, size, interpolation=cv2.INTER_AREA)

            hsv = to_hsv(frame)
            mask = clean_mask(create_mask(hsv, ranges), kernel_size)
            objects = find_objects(mask, min_area)
            detections = [((o.cx, o.cy), (o.x, o.y, o.w, o.h)) for o in objects]
            visible = tracker.update(detections, frame_idx)

            # --- draw results ---------------------------------------------
            for track in visible:
                color = track_color(track.track_id)
                x, y, w, h = track.box
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                cv2.circle(frame, track.centroid, 4, (255, 255, 255), -1)
                if draw_trails and len(track.trail) > 1:
                    pts = np.array(track.trail, dtype=np.int32).reshape(-1, 1, 2)
                    cv2.polylines(frame, [pts], False, color, 2, cv2.LINE_AA)
                draw_label(frame, f"ID {track.track_id}", x, y, color, 0.5)
            draw_hud(frame, frame_idx, total, len(objects), color_name)

            webm_writer.write(frame)
            if mp4_writer is not None:
                mp4_writer.write(frame)

            elapsed = (time.perf_counter() - t0) * 1000.0
            count = len(objects)
            if count:
                frames_with_det += 1
                total_det += count
            per_frame.append({
                "Frame": frame_idx + 1,
                "Time (s)": round(frame_idx / info.fps, 3),
                "Objects": count,
                "Active IDs": ",".join(str(t.track_id) for t in visible),
                "Processing (ms)": round(elapsed, 2),
            })

            if progress is not None:
                show = frame if (preview_every and frame_idx % preview_every == 0) else None
                progress(frame_idx + 1, total, show)
            frame_idx += 1
    finally:
        cap.release()
        webm_writer.release()
        if mp4_writer is not None:
            mp4_writer.release()

    if frame_idx == 0:
        raise ValueError("No frames could be read from this video.")

    total_seconds = time.perf_counter() - start_all
    avg_ms = float(np.mean([row["Processing (ms)"] for row in per_frame])) if per_frame else 0.0

    return VideoAnalysisResult(
        webm_path=webm_path,
        mp4_path=mp4_path,
        info=info,
        color_name=color_name,
        frames_processed=frame_idx,
        frames_with_detections=frames_with_det,
        total_detections=total_det,
        unique_tracks=tracker.total_tracks,
        avg_frame_ms=avg_ms,
        total_seconds=total_seconds,
        per_frame=per_frame,
        tracks=tracker.summary(),
        paths={tid: rec["path"] for tid, rec in tracker.history.items()},
        output_size=size,
        params={"kernel_size": kernel_size, "min_area": min_area, "max_distance": max_distance,
                "max_disappeared": max_disappeared, "max_width": max_width},
    )
