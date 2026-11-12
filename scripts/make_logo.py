"""Draw assets/logo.png (app icon): a hue ring around an indigo aperture."""

import os

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = 256
yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
cx = cy = (S - 1) / 2
r = np.hypot(xx - cx, yy - cy)
angle = (np.degrees(np.arctan2(yy - cy, xx - cx)) + 360) % 360

hsv = np.zeros((S, S, 3), np.uint8)
hsv[..., 0] = (angle / 2).astype(np.uint8)
hsv[..., 1] = 210
hsv[..., 2] = 255
ring = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

img = np.zeros((S, S, 4), np.uint8)
ring_mask = (r <= 124) & (r >= 92)
img[ring_mask, :3] = ring[ring_mask]
inner = r < 92
# indigo -> sky radial gradient in the centre (BGR)
t = np.clip(r / 92, 0, 1)[..., None]
grad = (np.array([241, 102, 99]) * (1 - t) + np.array([60, 30, 25]) * t)
img[inner, :3] = grad[inner].astype(np.uint8)
pupil = r < 34
img[pupil, :3] = (248, 250, 252)
img[r < 16, :3] = (32, 16, 11)
alpha = np.clip(125 - r, 0, 1) * 255
img[..., 3] = alpha.astype(np.uint8)
cv2.imwrite(os.path.join(ROOT, "assets", "logo.png"), img)
print("saved assets/logo.png")
