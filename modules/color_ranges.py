"""
Color definitions used throughout Chromatic Vision.

OpenCV stores HSV images with:
    Hue        -> 0 to 179  (the 0-360 degree colour wheel divided by 2)
    Saturation -> 0 to 255  (0 = grey, 255 = pure colour)
    Value      -> 0 to 255  (0 = black, 255 = full brightness)

Every colour is described as a LIST of (lower, upper) HSV ranges.
Most colours need one range. Red needs two, because red sits at BOTH ends
of the hue circle (around 0 and around 180), so a single [low, high]
interval cannot capture it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

HSVTuple = Tuple[int, int, int]
HSVRange = Tuple[HSVTuple, HSVTuple]


@dataclass
class ColorSpec:
    """A named colour with one or more HSV ranges and a display colour."""

    name: str
    ranges: List[HSVRange]
    hex: str                        # used by the UI for swatches and charts
    bgr: Tuple[int, int, int]       # used by OpenCV when drawing boxes
    description: str = ""
    tags: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Predefined colour presets (based on standard HSV hue bands and verified on
# the bundled sample images; they can be fine-tuned from the UI).
# ---------------------------------------------------------------------------
COLOR_PRESETS: dict[str, ColorSpec] = {
    "Red": ColorSpec(
        name="Red",
        ranges=[((0, 120, 70), (10, 255, 255)), ((170, 120, 70), (179, 255, 255))],
        hex="#EF4444",
        bgr=(68, 68, 239),
        description="Dual hue range (0-10 and 170-179) because red wraps around the hue circle.",
    ),
    "Orange": ColorSpec(
        name="Orange",
        ranges=[((11, 120, 100), (20, 255, 255))],
        hex="#F97316",
        bgr=(22, 115, 249),
        description="Hue 11-20, between red and yellow.",
    ),
    "Yellow": ColorSpec(
        name="Yellow",
        ranges=[((21, 100, 100), (34, 255, 255))],
        hex="#FACC15",
        bgr=(21, 204, 250),
        description="Hue 21-34, needs good brightness to separate from brown.",
    ),
    "Green": ColorSpec(
        name="Green",
        ranges=[((35, 60, 50), (85, 255, 255))],
        hex="#22C55E",
        bgr=(94, 197, 34),
        description="Hue 35-85, a wide band that covers light and dark greens.",
    ),
    "Blue": ColorSpec(
        name="Blue",
        ranges=[((95, 80, 50), (128, 255, 255))],
        hex="#3B82F6",
        bgr=(246, 130, 59),
        description="Hue 95-128, from sky blue to deep blue.",
    ),
    "Purple": ColorSpec(
        name="Purple",
        ranges=[((129, 60, 50), (160, 255, 255))],
        hex="#A855F7",
        bgr=(247, 85, 168),
        description="Hue 129-160, violet and magenta-purple tones.",
    ),
}

PRESET_NAMES = list(COLOR_PRESETS.keys())


def red_ranges(spread: int, s_min: int, v_min: int) -> List[HSVRange]:
    """Build the two red ranges from a single 'spread' value.

    spread = how many hue units on each side of 0/180 are treated as red.
    """
    spread = int(max(1, min(spread, 30)))
    return [
        ((0, s_min, v_min), (spread, 255, 255)),
        ((180 - spread, s_min, v_min), (179, 255, 255)),
    ]


def single_range(h_min: int, h_max: int, s_min: int, s_max: int,
                 v_min: int, v_max: int) -> List[HSVRange]:
    """Build a one-interval range list, keeping lower <= upper."""
    h_min, h_max = sorted((int(h_min), int(h_max)))
    s_min, s_max = sorted((int(s_min), int(s_max)))
    v_min, v_max = sorted((int(v_min), int(v_max)))
    return [((h_min, s_min, v_min), (h_max, s_max, v_max))]


def hsv_to_hex(h: int, s: int, v: int) -> str:
    """Convert an OpenCV HSV triple into a #RRGGBB string (for swatches)."""
    import colorsys

    r, g, b = colorsys.hsv_to_rgb(h / 179.0, s / 255.0, v / 255.0)
    return "#{:02X}{:02X}{:02X}".format(int(r * 255), int(g * 255), int(b * 255))


def hex_to_bgr(hex_color: str) -> Tuple[int, int, int]:
    """Convert '#RRGGBB' into an OpenCV BGR tuple."""
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return (b, g, r)


def describe_ranges(ranges: List[HSVRange]) -> str:
    """Human-readable text such as 'H 0-10 | S 120-255 | V 70-255'."""
    parts = []
    for lo, hi in ranges:
        parts.append(f"H {lo[0]}-{hi[0]} · S {lo[1]}-{hi[1]} · V {lo[2]}-{hi[2]}")
    return "  +  ".join(parts)
