"""Shared pytest fixtures and helpers."""

import json
import os
import sys

import cv2
import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

SAMPLE_IMAGES = os.path.join(ROOT, "assets", "sample_images")
SAMPLE_VIDEOS = os.path.join(ROOT, "assets", "sample_videos")


@pytest.fixture(scope="session")
def ground_truth():
    with open(os.path.join(ROOT, "assets", "sample_ground_truth.json"), encoding="utf-8") as fh:
        return json.load(fh)


def bgr_from_hsv(h, s=230, v=230):
    px = np.uint8([[[h, s, v]]])
    return tuple(int(c) for c in cv2.cvtColor(px, cv2.COLOR_HSV2BGR)[0, 0])


@pytest.fixture
def blank():
    """A plain dark-grey 400x300 image."""
    return np.full((300, 400, 3), 40, dtype=np.uint8)
