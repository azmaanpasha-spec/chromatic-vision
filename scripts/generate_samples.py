"""
Generate the bundled sample images and videos for the demo mode.

Run from the project root:
    python scripts/generate_samples.py

Everything is synthetic (drawn with OpenCV + NumPy) so the project has no
licensing issues and the ground truth (how many objects of each colour
exist) is known exactly. That ground truth is saved to
assets/sample_ground_truth.json and used by the automated tests.
"""

from __future__ import annotations

import json
import os
import sys

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_DIR = os.path.join(ROOT, "assets", "sample_images")
VID_DIR = os.path.join(ROOT, "assets", "sample_videos")
rng = np.random.default_rng(42)

# OpenCV hue (0-179) of each colour used in the samples
HUES = {"Red": 0, "Orange": 15, "Yellow": 28, "Green": 60, "Blue": 112, "Purple": 142}


def background(w: int, h: int, top=(52, 44, 38), bottom=(30, 26, 22), noise: float = 6.0) -> np.ndarray:
    """Neutral vertical gradient with mild sensor-like noise."""
    t = np.linspace(0, 1, h)[:, None, None]
    img = (np.array(top) * (1 - t) + np.array(bottom) * t) * np.ones((h, w, 3))
    img += rng.normal(0, noise, img.shape)
    return np.clip(img, 0, 255).astype(np.uint8)


def shaded_ball(img: np.ndarray, center, radius: int, hue: int, sat: int = 225) -> None:
    """Draw a ball with a soft highlight (brightness varies, hue stays constant)."""
    cx, cy = center
    h, w = img.shape[:2]
    x0, x1 = max(0, cx - radius), min(w, cx + radius + 1)
    y0, y1 = max(0, cy - radius), min(h, cy + radius + 1)
    if x0 >= x1 or y0 >= y1:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    inside = dist <= radius
    # highlight offset towards the top-left
    hl = np.sqrt((xx - (cx - radius * 0.35)) ** 2 + (yy - (cy - radius * 0.35)) ** 2) / (radius * 1.6)
    value = np.clip(255 - 110 * hl, 120, 255)
    patch_hsv = np.zeros((y1 - y0, x1 - x0, 3), np.uint8)
    patch_hsv[..., 0] = hue
    patch_hsv[..., 1] = np.clip(sat - 40 * (1 - hl), 150, 255)
    patch_hsv[..., 2] = value
    patch_bgr = cv2.cvtColor(patch_hsv, cv2.COLOR_HSV2BGR)
    region = img[y0:y1, x0:x1]
    region[inside] = patch_bgr[inside]


def flat_color(hue: int, sat: int = 220, val: int = 225):
    px = np.uint8([[[hue, sat, val]]])
    return tuple(int(c) for c in cv2.cvtColor(px, cv2.COLOR_HSV2BGR)[0, 0])


def add_noise(img: np.ndarray, sigma: float = 4.0) -> np.ndarray:
    return np.clip(img.astype(np.float32) + rng.normal(0, sigma, img.shape), 0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------
def make_shapes_scene() -> dict:
    """Mixed geometric shapes in all six preset colours plus neutral distractors."""
    w, h = 1280, 800
    img = background(w, h)
    counts = {k: 0 for k in HUES}

    def rect(name, x, y, rw, rh):
        cv2.rectangle(img, (x, y), (x + rw, y + rh), flat_color(HUES[name]), -1)
        counts[name] += 1

    def circ(name, x, y, r):
        shaded_ball(img, (x, y), r, HUES[name])
        counts[name] += 1

    def tri(name, pts):
        cv2.fillPoly(img, [np.array(pts, np.int32)], flat_color(HUES[name]))
        counts[name] += 1

    # Red x3
    circ("Red", 160, 160, 70); rect("Red", 900, 560, 140, 110); tri("Red", [(560, 700), (660, 520), (760, 700)])
    # Blue x3
    circ("Blue", 420, 150, 60); rect("Blue", 1050, 90, 150, 120); circ("Blue", 700, 380, 55)
    # Green x3
    rect("Green", 80, 380, 160, 120); circ("Green", 1150, 380, 75); tri("Green", [(300, 720), (380, 560), (460, 720)])
    # Yellow x2
    circ("Yellow", 650, 140, 65); rect("Yellow", 420, 400, 120, 90)
    # Orange x2
    circ("Orange", 880, 180, 60); rect("Orange", 60, 600, 110, 130)
    # Purple x2
    circ("Purple", 950, 400, 60); tri("Purple", [(1100, 760), (1180, 600), (1260, 760)])

    # Neutral distractors (white, grey, dark) - should never be detected as a colour
    cv2.rectangle(img, (240, 260), (330, 330), (235, 235, 235), -1)
    cv2.circle(img, (820, 720), 40, (128, 128, 128), -1)
    cv2.rectangle(img, (560, 250), (640, 300), (35, 35, 35), -1)

    img = add_noise(img, 3.5)
    cv2.imwrite(os.path.join(IMG_DIR, "shapes_scene.png"), img)
    return counts


def make_ball_pit() -> dict:
    """Shaded balls of three colours on a darker background (like a toy photo)."""
    w, h = 1000, 640
    img = background(w, h, top=(70, 62, 58), bottom=(38, 34, 32), noise=7)
    layout = {
        "Red": [(140, 150), (420, 470), (820, 180), (650, 520)],
        "Blue": [(320, 200), (560, 300), (880, 470)],
        "Green": [(170, 470), (720, 120)],
    }
    for name, centers in layout.items():
        for c in centers:
            shaded_ball(img, c, 62, HUES[name])
    img = add_noise(img, 4)
    cv2.imwrite(os.path.join(IMG_DIR, "ball_collection.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return {k: len(v) for k, v in layout.items()}


def make_neutral() -> dict:
    """A scene containing only grey/white/black objects (no colour matches)."""
    w, h = 900, 600
    img = background(w, h, top=(90, 90, 90), bottom=(50, 50, 50), noise=5)
    cv2.rectangle(img, (100, 100), (300, 260), (230, 230, 230), -1)
    cv2.circle(img, (600, 300), 110, (140, 140, 140), -1)
    cv2.rectangle(img, (350, 380), (520, 520), (25, 25, 25), -1)
    img = add_noise(img, 3)
    cv2.imwrite(os.path.join(IMG_DIR, "neutral_scene.png"), img)
    return {k: 0 for k in HUES}


# ---------------------------------------------------------------------------
# Videos
# ---------------------------------------------------------------------------
def make_moving_objects(path: str, fourcc: str, frames: int = 200, fps: int = 25) -> dict:
    """Several coloured objects moving on known paths.

    * Two red balls in separate lanes (tests multi-object tracking of one colour)
    * A blue ball bouncing around the frame
    * A green square sliding left to right
    * A yellow ball on a sine path
    * A dark grey pillar in the centre that briefly hides the lower red ball
      (tests 'disappeared' handling - the ID should survive the occlusion)
    """
    w, h = 640, 360
    writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*fourcc), fps, (w, h))
    if not writer.isOpened():
        raise RuntimeError(f"Cannot write {path} with codec {fourcc}")
    base = background(w, h, noise=0)
    bx, by, vx, vy = 120.0, 90.0, 4.2, 3.1
    for i in range(frames):
        frame = base.copy()
        t = i / frames
        # red ball 1: upper lane, left -> right
        shaded_ball(frame, (int(40 + t * 560), 70), 24, HUES["Red"])
        # red ball 2: lower lane, right -> left (passes behind the pillar)
        shaded_ball(frame, (int(600 - t * 560), 290), 24, HUES["Red"])
        # blue bouncing ball
        bx += vx; by += vy
        if bx < 26 or bx > w - 26: vx = -vx
        if by < 26 or by > h - 26: vy = -vy
        shaded_ball(frame, (int(bx), int(by)), 22, HUES["Blue"])
        # green square
        gx = int(20 + t * 580)
        cv2.rectangle(frame, (gx, 160), (gx + 40, 200), flat_color(HUES["Green"]), -1)
        # yellow sine ball
        yx = int(600 - t * 540)
        yy = int(180 + 60 * np.sin(t * 4 * np.pi))
        shaded_ball(frame, (yx, yy), 18, HUES["Yellow"])
        # occluding pillar (only over the lower lane)
        cv2.rectangle(frame, (300, 250), (350, 335), (60, 60, 64), -1)
        frame = add_noise(frame, 3)
        writer.write(frame)
    writer.release()
    return {"frames": frames, "fps": fps, "objects": {"Red": 2, "Blue": 1, "Green": 1, "Yellow": 1}}


def make_single_ball(path: str, fourcc: str, frames: int = 120, fps: int = 30) -> dict:
    """One orange ball moving along a circle - the simplest tracking demo."""
    w, h = 480, 360
    writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*fourcc), fps, (w, h))
    if not writer.isOpened():
        raise RuntimeError(f"Cannot write {path} with codec {fourcc}")
    base = background(w, h, top=(40, 36, 30), bottom=(24, 20, 18), noise=0)
    for i in range(frames):
        frame = base.copy()
        a = 2 * np.pi * i / frames
        shaded_ball(frame, (int(240 + 140 * np.cos(a)), int(180 + 110 * np.sin(a))), 26, HUES["Orange"])
        writer.write(add_noise(frame, 3))
    writer.release()
    return {"frames": frames, "fps": fps, "objects": {"Orange": 1}}


def main() -> int:
    os.makedirs(IMG_DIR, exist_ok=True)
    os.makedirs(VID_DIR, exist_ok=True)
    truth = {
        "images": {
            "shapes_scene.png": make_shapes_scene(),
            "ball_collection.jpg": make_ball_pit(),
            "neutral_scene.png": make_neutral(),
        },
        "videos": {
            "moving_objects.mp4": make_moving_objects(os.path.join(VID_DIR, "moving_objects.mp4"), "mp4v"),
            "orbiting_ball.avi": make_single_ball(os.path.join(VID_DIR, "orbiting_ball.avi"), "MJPG"),
        },
    }
    with open(os.path.join(ROOT, "assets", "sample_ground_truth.json"), "w", encoding="utf-8") as fh:
        json.dump(truth, fh, indent=2)
    print(json.dumps(truth, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
