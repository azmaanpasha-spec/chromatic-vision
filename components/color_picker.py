"""Target-colour selector shared by the image and video studios."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import streamlit as st

from modules.color_ranges import (COLOR_PRESETS, PRESET_NAMES, HSVRange, describe_ranges, hex_to_bgr,
                                  hsv_to_hex, red_ranges, single_range)

from .ui_components import color_swatch, label

SWATCH_DOT = {"Red": "🔴", "Orange": "🟠", "Yellow": "🟡", "Green": "🟢", "Blue": "🔵",
              "Purple": "🟣", "Custom": "🎛️"}


@dataclass
class ColorSelection:
    name: str
    ranges: List[HSVRange]
    hex: str
    bgr: Tuple[int, int, int]


def color_selector(prefix: str, default: str = "Red") -> ColorSelection:
    """Palette + optional HSV fine-tuning. Returns the active selection."""
    label("Target colour")
    options = PRESET_NAMES + ["Custom"]
    key = f"{prefix}_color"
    if key not in st.session_state or st.session_state[key] not in options:
        st.session_state[key] = default
    choice = st.segmented_control(
        "Target colour", options, key=key, required=True, label_visibility="collapsed",
        format_func=lambda c: f"{SWATCH_DOT[c]} {c}", width="stretch",
    ) or default

    if choice == "Custom":
        with st.container():
            st.caption("Define any colour with your own HSV range (OpenCV scale: H 0-179, S/V 0-255).")
            h = st.slider("Hue range", 0, 179, (40, 80), key=f"{prefix}_c_h")
            s = st.slider("Saturation range", 0, 255, (70, 255), key=f"{prefix}_c_s")
            v = st.slider("Value (brightness) range", 0, 255, (60, 255), key=f"{prefix}_c_v")
        ranges = single_range(h[0], h[1], s[0], s[1], v[0], v[1])
        mid_h = (h[0] + h[1]) // 2
        hex_color = hsv_to_hex(mid_h, max(s[0], 180), 235)
        selection = ColorSelection("Custom", ranges, hex_color, hex_to_bgr(hex_color))
    else:
        spec = COLOR_PRESETS[choice]
        ranges = spec.ranges
        with st.expander("Fine-tune HSV thresholds", icon=":material/tune:"):
            lo0, hi0 = spec.ranges[0]
            if choice == "Red":
                st.caption("Red wraps around the hue circle, so two ranges are used: "
                           "0 → spread and (179 − spread) → 179.")
                spread = st.slider("Hue spread", 3, 25, hi0[0], key=f"{prefix}_{choice}_spread")
                s_min = st.slider("Minimum saturation", 0, 255, lo0[1], key=f"{prefix}_{choice}_s")
                v_min = st.slider("Minimum brightness (value)", 0, 255, lo0[2], key=f"{prefix}_{choice}_v")
                ranges = red_ranges(spread, s_min, v_min)
            else:
                h = st.slider("Hue range", 0, 179, (lo0[0], hi0[0]), key=f"{prefix}_{choice}_h")
                s_min = st.slider("Minimum saturation", 0, 255, lo0[1], key=f"{prefix}_{choice}_s")
                v_min = st.slider("Minimum brightness (value)", 0, 255, lo0[2], key=f"{prefix}_{choice}_v")
                ranges = single_range(h[0], h[1], s_min, 255, v_min, 255)
        selection = ColorSelection(choice, ranges, spec.hex, spec.bgr)

    color_swatch(selection.name, selection.hex, describe_ranges(selection.ranges),
                 [(lo[0], hi[0]) for lo, hi in selection.ranges])
    return selection
