"""
Image processing pipeline for colour-based object detection.

Pipeline (each step is a separate, documented function):

    1. load_image_from_bytes   -> decode JPG/PNG bytes into a BGR NumPy array
    2. to_hsv                  -> convert BGR to HSV colour space
    3. create_mask             -> threshold with cv2.inRange (binary mask)
    4. apply_morphology        -> erosion, dilation, opening, closing
    5. find_objects            -> cv2.findContours + cv2.boundingRect + centroids
    6. draw_detections         -> draw bounding boxes, labels and centroids
    7. analyze_image           -> runs the full pipeline and returns a result object
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

import cv2
import numpy as np

from .color_ranges import HSVRange

# Very large photos are scaled down before processing. This keeps memory
# usage and processing time reasonable without affecting detection quality.
MAX_IMAGE_SIDE = 1600


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class DetectedObject:
    """One connected region of the target colour."""

    object_id: int
    x: int
    y: int
    w: int
    h: int
    area: float          # contour area in pixels
    cx: int              # centroid x
    cy: int              # centroid y

    def as_dict(self) -> Dict[str, float]:
        return {
            "ID": self.object_id,
            "X": self.x,
            "Y": self.y,
            "Width": self.w,
            "Height": self.h,
            "Area (px)": round(self.area, 1),
            "Centroid X": self.cx,
            "Centroid Y": self.cy,
        }


@dataclass
class ImageAnalysisResult:
    """Everything produced by one run of the image pipeline."""

    original: np.ndarray            # BGR (possibly resized) input
    hsv: np.ndarray                 # HSV version of the input
    raw_mask: np.ndarray            # mask straight from cv2.inRange
    stages: Dict[str, np.ndarray]   # morphological intermediate masks
    clean_mask: np.ndarray          # final mask after opening + closing
    segmented: np.ndarray           # original pixels where mask == 255
    annotated: np.ndarray           # original with boxes and labels
    objects: List[DetectedObject]
    coverage_percent: float         # % of image pixels that match the colour
    processing_ms: float
    color_name: str
    ranges: List[HSVRange]
    original_size: Tuple[int, int]  # (width, height) before any resizing
    params: Dict[str, int] = field(default_factory=dict)

    @property
    def object_count(self) -> int:
        return len(self.objects)

    @property
    def size(self) -> Tuple[int, int]:
        h, w = self.original.shape[:2]
        return w, h


# ---------------------------------------------------------------------------
# 1. Loading
# ---------------------------------------------------------------------------
def load_image_from_bytes(data: bytes) -> np.ndarray:
    """Decode image bytes (JPG / PNG) into a BGR image.

    Raises ValueError for empty or unreadable data so the UI can show a
    friendly error instead of crashing.
    """
    if not data:
        raise ValueError("The uploaded file is empty.")
    buffer = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if image is None or image.size == 0:
        raise ValueError("The file could not be decoded as an image. "
                         "Please upload a valid JPG, JPEG or PNG file.")
    return image


def load_image_from_path(path: str) -> np.ndarray:
    """Read an image from disk (used for the bundled samples)."""
    with open(path, "rb") as fh:
        return load_image_from_bytes(fh.read())


def limit_size(image: np.ndarray, max_side: int = MAX_IMAGE_SIDE) -> np.ndarray:
    """Scale an image down so its longest side is at most max_side."""
    h, w = image.shape[:2]
    longest = max(h, w)
    if longest <= max_side:
        return image
    scale = max_side / float(longest)
    return cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)


# ---------------------------------------------------------------------------
# 2-3. Colour space conversion and thresholding
# ---------------------------------------------------------------------------
def to_hsv(image_bgr: np.ndarray) -> np.ndarray:
    """Convert BGR to HSV. HSV separates colour (hue) from brightness,
    which makes colour thresholds far more robust to lighting changes."""
    return cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)


def create_mask(hsv: np.ndarray, ranges: Sequence[HSVRange]) -> np.ndarray:
    """Binary mask: 255 where a pixel falls inside ANY of the HSV ranges.

    cv2.inRange returns 255 for pixels between lower and upper (inclusive)
    and 0 otherwise. Multiple ranges (e.g. red) are merged with bitwise OR.
    """
    mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
    for lower, upper in ranges:
        part = cv2.inRange(hsv, np.array(lower, dtype=np.uint8), np.array(upper, dtype=np.uint8))
        mask = cv2.bitwise_or(mask, part)
    return mask


# ---------------------------------------------------------------------------
# 4. Morphological operations
# ---------------------------------------------------------------------------
def make_kernel(size: int) -> np.ndarray:
    """Elliptical structuring element (rounder results than a square)."""
    size = max(1, int(size))
    if size % 2 == 0:
        size += 1
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))


def apply_morphology(mask: np.ndarray, kernel_size: int = 5,
                     iterations: int = 1) -> Dict[str, np.ndarray]:
    """Clean a binary mask and return every intermediate stage.

    erosion  : shrinks white regions -> removes tiny specks of noise
    dilation : grows white regions   -> fills small gaps
    opening  : erosion then dilation -> removes noise, keeps object size
    closing  : dilation then erosion -> fills holes inside objects

    The final clean mask is opening followed by closing.
    """
    kernel = make_kernel(kernel_size)
    eroded = cv2.erode(mask, kernel, iterations=iterations)
    dilated = cv2.dilate(mask, kernel, iterations=iterations)
    opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=iterations)
    closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel, iterations=iterations)
    return {
        "Eroded": eroded,
        "Dilated": dilated,
        "Opened": opened,
        "Opened + Closed": closed,
    }


def clean_mask(mask: np.ndarray, kernel_size: int = 5, iterations: int = 1) -> np.ndarray:
    """Fast path used for video frames: opening followed by closing only."""
    kernel = make_kernel(kernel_size)
    opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=iterations)
    return cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel, iterations=iterations)


# ---------------------------------------------------------------------------
# 5. Contours, bounding boxes and centroids
# ---------------------------------------------------------------------------
def contour_centroid(contour: np.ndarray, fallback: Tuple[int, int]) -> Tuple[int, int]:
    """Centroid from image moments: cx = m10/m00, cy = m01/m00."""
    m = cv2.moments(contour)
    if m["m00"] == 0:
        return fallback
    return int(m["m10"] / m["m00"]), int(m["m01"] / m["m00"])


def find_objects(mask: np.ndarray, min_area: int = 300) -> List[DetectedObject]:
    """Find external contours in the mask and describe each one.

    Contours smaller than min_area pixels are ignored as noise.
    Objects are sorted from largest to smallest.
    """
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    found = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        cx, cy = contour_centroid(contour, (x + w // 2, y + h // 2))
        found.append((area, x, y, w, h, cx, cy))

    found.sort(key=lambda item: item[0], reverse=True)
    return [
        DetectedObject(object_id=i + 1, x=x, y=y, w=w, h=h, area=area, cx=cx, cy=cy)
        for i, (area, x, y, w, h, cx, cy) in enumerate(found)
    ]


# ---------------------------------------------------------------------------
# 6. Drawing
# ---------------------------------------------------------------------------
def draw_label(image: np.ndarray, text: str, x: int, y: int,
               color: Tuple[int, int, int], scale: float = 0.5) -> None:
    """Draw text on a filled rectangle so it is readable on any background."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    thickness = 1 if scale < 0.6 else 2
    (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)
    top = max(0, y - th - baseline - 6)
    cv2.rectangle(image, (x, top), (x + tw + 8, top + th + baseline + 6), color, -1)
    # choose black or white text depending on the label brightness
    brightness = 0.299 * color[2] + 0.587 * color[1] + 0.114 * color[0]
    text_color = (20, 16, 11) if brightness > 150 else (255, 255, 255)
    cv2.putText(image, text, (x + 4, top + th + 3), font, scale, text_color, thickness, cv2.LINE_AA)


def draw_detections(image_bgr: np.ndarray, objects: Sequence[DetectedObject],
                    color: Tuple[int, int, int], label: str = "") -> np.ndarray:
    """Return a copy of the image with boxes, labels and centroid markers."""
    output = image_bgr.copy()
    h, w = output.shape[:2]
    thickness = max(2, int(round(max(h, w) / 500)))
    scale = max(0.45, min(1.0, max(h, w) / 1400))
    for obj in objects:
        cv2.rectangle(output, (obj.x, obj.y), (obj.x + obj.w, obj.y + obj.h), color, thickness)
        cv2.circle(output, (obj.cx, obj.cy), thickness + 2, (255, 255, 255), -1)
        cv2.circle(output, (obj.cx, obj.cy), thickness + 2, color, 1)
        text = f"{label} #{obj.object_id}".strip()
        draw_label(output, text, obj.x, obj.y, color, scale)
    return output


# ---------------------------------------------------------------------------
# 7. Full pipeline
# ---------------------------------------------------------------------------
def analyze_image(image_bgr: np.ndarray, ranges: Sequence[HSVRange], color_name: str,
                  box_color: Tuple[int, int, int], kernel_size: int = 5,
                  iterations: int = 1, min_area: int = 300) -> ImageAnalysisResult:
    """Run the complete colour detection pipeline on one image."""
    if image_bgr is None or image_bgr.size == 0:
        raise ValueError("Empty image - nothing to analyse.")

    original_h, original_w = image_bgr.shape[:2]
    start = time.perf_counter()

    image = limit_size(image_bgr)
    hsv = to_hsv(image)
    raw = create_mask(hsv, ranges)
    stages = apply_morphology(raw, kernel_size, iterations)
    final_mask = stages["Opened + Closed"]
    objects = find_objects(final_mask, min_area)
    segmented = cv2.bitwise_and(image, image, mask=final_mask)
    annotated = draw_detections(image, objects, box_color, color_name)

    elapsed_ms = (time.perf_counter() - start) * 1000.0
    coverage = 100.0 * float(np.count_nonzero(final_mask)) / float(final_mask.size)

    return ImageAnalysisResult(
        original=image,
        hsv=hsv,
        raw_mask=raw,
        stages=stages,
        clean_mask=final_mask,
        segmented=segmented,
        annotated=annotated,
        objects=objects,
        coverage_percent=coverage,
        processing_ms=elapsed_ms,
        color_name=color_name,
        ranges=list(ranges),
        original_size=(original_w, original_h),
        params={"kernel_size": kernel_size, "iterations": iterations, "min_area": min_area},
    )


# ---------------------------------------------------------------------------
# Helpers for the UI
# ---------------------------------------------------------------------------
def bgr_to_rgb(image: np.ndarray) -> np.ndarray:
    """Streamlit / Pillow expect RGB; OpenCV uses BGR."""
    if image.ndim == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def encode_png(image: np.ndarray) -> bytes:
    """Encode a BGR or grayscale image as PNG bytes for downloading."""
    ok, buffer = cv2.imencode(".png", image)
    if not ok:
        raise ValueError("Could not encode image as PNG.")
    return buffer.tobytes()
