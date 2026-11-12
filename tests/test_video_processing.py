"""Tests for modules/video_processing.py (uses the bundled sample videos)."""

import os

import cv2
import numpy as np
import pytest

from conftest import SAMPLE_VIDEOS
from modules.color_ranges import COLOR_PRESETS
from modules.video_processing import get_video_info, make_preview, process_video


def process(path, color, out_dir, **kw):
    spec = COLOR_PRESETS[color]
    return process_video(path, str(out_dir), spec.ranges, color, **kw)


def count_frames(path):
    cap = cv2.VideoCapture(path)
    n = 0
    while cap.read()[0]:
        n += 1
    cap.release()
    return n


# TC-07 ---------------------------------------------------------------
def test_video_info():
    info = get_video_info(os.path.join(SAMPLE_VIDEOS, "moving_objects.mp4"))
    assert (info.width, info.height) == (640, 360)
    assert info.frame_count == 200
    assert info.fps == pytest.approx(25.0)
    assert info.duration == pytest.approx(8.0)


def test_avi_input_supported():
    info = get_video_info(os.path.join(SAMPLE_VIDEOS, "orbiting_ball.avi"))
    assert info.frame_count == 120 and info.fps == pytest.approx(30.0)


# TC-08 ---------------------------------------------------------------
def test_tracking_two_red_balls(tmp_path):
    """Two red balls -> exactly two IDs for the whole clip, despite the occlusion."""
    result = process(os.path.join(SAMPLE_VIDEOS, "moving_objects.mp4"), "Red", tmp_path)
    assert result.frames_processed == 200
    assert result.unique_tracks == 2
    assert result.max_objects_in_frame == 2
    assert all(t["Last frame"] == 199 for t in result.tracks)


def test_single_orange_ball_one_id(tmp_path):
    result = process(os.path.join(SAMPLE_VIDEOS, "orbiting_ball.avi"), "Orange", tmp_path)
    assert result.frames_with_detections == 120
    assert result.unique_tracks == 1
    assert result.detection_frequency == pytest.approx(100.0)


# TC-10 (output files are valid, readable videos) ---------------------
def test_output_videos_can_be_opened(tmp_path):
    result = process(os.path.join(SAMPLE_VIDEOS, "moving_objects.mp4"), "Blue", tmp_path, max_frames=60)
    assert result.frames_processed == 60
    for path in (result.webm_path, result.mp4_path):
        assert path and os.path.getsize(path) > 10_000
        assert count_frames(path) == 60


def test_video_with_no_detections(tmp_path):
    """Purple does not appear in the sample video: no crash, zero detections."""
    result = process(os.path.join(SAMPLE_VIDEOS, "moving_objects.mp4"), "Purple", tmp_path, max_frames=40)
    assert result.frames_with_detections == 0
    assert result.unique_tracks == 0
    assert result.detection_frequency == 0.0
    assert os.path.getsize(result.webm_path) > 0


def test_resizing_wide_video(tmp_path):
    path = str(tmp_path / "wide.mp4")
    w = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), 10, (1920, 1080))
    for _ in range(5):
        w.write(np.full((1080, 1920, 3), 30, np.uint8))
    w.release()
    result = process(path, "Red", tmp_path, max_width=960)
    assert result.output_size == (960, 540)


def test_mov_container_supported(tmp_path):
    path = str(tmp_path / "clip.mov")
    w = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), 20, (320, 240))
    for i in range(20):
        frame = np.full((240, 320, 3), 30, np.uint8)
        cv2.circle(frame, (40 + 10 * i, 120), 15, (40, 40, 230), -1)  # red ball (BGR)
        w.write(frame)
    w.release()
    result = process(path, "Red", tmp_path, min_area=100)
    assert result.frames_processed == 20 and result.unique_tracks == 1


def test_invalid_video_raises(tmp_path):
    bad = tmp_path / "broken.mp4"
    bad.write_bytes(b"this is not a video")
    with pytest.raises(ValueError):
        get_video_info(str(bad))


def test_empty_video_file_raises(tmp_path):
    empty = tmp_path / "empty.avi"
    empty.write_bytes(b"")
    with pytest.raises(ValueError):
        get_video_info(str(empty))


def test_preview_is_created(tmp_path):
    preview = make_preview(os.path.join(SAMPLE_VIDEOS, "orbiting_ball.avi"), str(tmp_path), max_seconds=2)
    assert preview and count_frames(preview) == 60
