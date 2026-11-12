"""Tests for modules/image_processing.py and modules/color_ranges.py."""

import os

import cv2
import numpy as np
import pytest

from conftest import SAMPLE_IMAGES, bgr_from_hsv
from modules.analytics import color_distribution
from modules.color_ranges import COLOR_PRESETS, red_ranges
from modules.image_processing import (analyze_image, apply_morphology, create_mask, encode_png, find_objects,
                                      load_image_from_bytes, load_image_from_path, to_hsv)


def run(image, color):
    spec = COLOR_PRESETS[color]
    return analyze_image(image, spec.ranges, color, spec.bgr)


# TC-01 ---------------------------------------------------------------
def test_red_detection_both_hue_ends(blank):
    """Red at hue 2 AND hue 176 must both be found (dual HSV range)."""
    img = blank.copy()
    cv2.rectangle(img, (20, 20), (120, 120), bgr_from_hsv(2), -1)
    cv2.rectangle(img, (200, 100), (320, 220), bgr_from_hsv(176), -1)
    result = run(img, "Red")
    assert result.object_count == 2


def test_single_red_range_would_miss_one_end(blank):
    """Demonstrates WHY two ranges are needed: only the low range finds one object."""
    img = blank.copy()
    cv2.rectangle(img, (20, 20), (120, 120), bgr_from_hsv(2), -1)
    cv2.rectangle(img, (200, 100), (320, 220), bgr_from_hsv(176), -1)
    low_only = [COLOR_PRESETS["Red"].ranges[0]]
    mask = create_mask(to_hsv(img), low_only)
    assert len(find_objects(mask, 300)) == 1


# TC-02 ---------------------------------------------------------------
def test_blue_detection(blank):
    img = blank.copy()
    cv2.circle(img, (200, 150), 60, bgr_from_hsv(112), -1)
    result = run(img, "Blue")
    assert result.object_count == 1
    obj = result.objects[0]
    assert abs(obj.cx - 200) <= 2 and abs(obj.cy - 150) <= 2  # centroid at circle centre


# TC-03 ---------------------------------------------------------------
def test_green_detection(blank):
    img = blank.copy()
    cv2.rectangle(img, (50, 50), (150, 200), bgr_from_hsv(60), -1)
    result = run(img, "Green")
    assert result.object_count == 1
    o = result.objects[0]
    assert (o.x, o.y) == (50, 50) and (o.w, o.h) == (101, 151)  # boundingRect is inclusive


# TC-04 ---------------------------------------------------------------
def test_multiple_objects_on_sample_scene(ground_truth):
    """Every preset colour on every bundled sample matches the known ground truth."""
    for filename, counts in ground_truth["images"].items():
        img = load_image_from_path(os.path.join(SAMPLE_IMAGES, filename))
        for color, expected in counts.items():
            assert run(img, color).object_count == expected, f"{filename} / {color}"


# TC-05 ---------------------------------------------------------------
def test_no_matching_colour(blank):
    img = blank.copy()
    cv2.rectangle(img, (50, 50), (150, 150), (255, 255, 255), -1)  # white
    cv2.rectangle(img, (200, 50), (300, 150), (128, 128, 128), -1)  # grey
    for color in COLOR_PRESETS:
        result = run(img, color)
        assert result.object_count == 0
        assert result.coverage_percent == 0.0


# TC-06 ---------------------------------------------------------------
@pytest.mark.parametrize("data", [b"", b"not an image at all", b"\x89PNG\r\n\x1a\n broken"])
def test_invalid_image_bytes_raise_value_error(data):
    with pytest.raises(ValueError):
        load_image_from_bytes(data)


def test_empty_array_rejected():
    with pytest.raises(ValueError):
        analyze_image(np.zeros((0, 0, 3), np.uint8), COLOR_PRESETS["Red"].ranges, "Red", (0, 0, 255))


# Morphology and helpers ------------------------------------------------
def test_opening_removes_isolated_noise():
    mask = np.zeros((200, 200), np.uint8)
    cv2.rectangle(mask, (50, 50), (150, 150), 255, -1)
    rng = np.random.default_rng(0)
    ys, xs = rng.integers(0, 200, 300), rng.integers(0, 200, 300)
    mask[ys, xs] = 255  # salt noise
    stages = apply_morphology(mask, kernel_size=5)
    contours, _ = cv2.findContours(stages["Opened + Closed"], cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    assert len(contours) == 1


def test_closing_fills_hole():
    mask = np.zeros((200, 200), np.uint8)
    cv2.circle(mask, (100, 100), 60, 255, -1)
    cv2.circle(mask, (100, 100), 2, 0, -1)  # small hole (like a specular highlight)
    closed = apply_morphology(mask, kernel_size=7)["Opened + Closed"]
    assert closed[100, 100] == 255


def test_min_area_filters_small_objects(blank):
    img = blank.copy()
    cv2.rectangle(img, (10, 10), (20, 20), bgr_from_hsv(60), -1)      # ~121 px
    cv2.rectangle(img, (100, 100), (200, 200), bgr_from_hsv(60), -1)  # ~10k px
    spec = COLOR_PRESETS["Green"]
    assert analyze_image(img, spec.ranges, "Green", spec.bgr, min_area=300).object_count == 1
    assert analyze_image(img, spec.ranges, "Green", spec.bgr, min_area=50).object_count == 2


def test_large_image_is_scaled_down():
    img = np.zeros((3000, 4000, 3), np.uint8)
    result = run(img, "Blue")
    assert max(result.size) == 1600
    assert result.original_size == (4000, 3000)


def test_red_ranges_builder():
    lo, hi = red_ranges(10, 120, 70)
    assert lo == ((0, 120, 70), (10, 255, 255))
    assert hi == ((170, 120, 70), (179, 255, 255))


# TC-09 (download payload) --------------------------------------------
def test_processed_image_png_roundtrip():
    img = load_image_from_path(os.path.join(SAMPLE_IMAGES, "shapes_scene.png"))
    result = run(img, "Red")
    data = encode_png(result.annotated)
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    decoded = load_image_from_bytes(data)
    assert decoded.shape == result.annotated.shape


def test_colour_distribution_sums_to_100():
    img = load_image_from_path(os.path.join(SAMPLE_IMAGES, "shapes_scene.png"))
    dist = color_distribution(img)
    assert abs(sum(dist.values()) - 100.0) < 0.01
    assert dist["Red"] > 0 and dist["Blue"] > 0
