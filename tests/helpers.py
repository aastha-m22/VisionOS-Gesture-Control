"""Shared helpers for constructing synthetic :class:`HandLandmarks` poses.

Real MediaPipe output is unavailable in CI, so these builders place the 21
landmarks deterministically to reproduce canonical gestures. Geometry is chosen
so the resulting hand-scale, finger-extension and pinch distances exercise the
rule thresholds exactly as a real hand would.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from visionos.core.landmark import HandLandmarks

# Horizontal positions of the four finger columns (well separated so a thumb
# touching one fingertip is not accidentally close to its neighbour).
_FINGER_X = {"index": 0.40, "middle": 0.52, "ring": 0.62, "pinky": 0.70}
_FINGER_SLOTS = (  # (mcp, pip, dip, tip, column-key)
    (5, 6, 7, 8, "index"),
    (9, 10, 11, 12, "middle"),
    (13, 14, 15, 16, "ring"),
    (17, 18, 19, 20, "pinky"),
)

Coord = Tuple[float, float, float]


def build_hand(
    index: bool,
    middle: bool,
    ring: bool,
    pinky: bool,
    thumb_tip: Tuple[float, float],
) -> HandLandmarks:
    """Build a hand with the given finger-extension states and thumb position."""
    pts: List[Optional[Coord]] = [None] * 21
    pts[0] = (0.50, 0.95, 0.0)  # wrist
    extended = {"index": index, "middle": middle, "ring": ring, "pinky": pinky}

    for mcp, pip, dip, tip, key in _FINGER_SLOTS:
        x = _FINGER_X[key]
        pts[mcp] = (x, 0.65, 0.0)
        if extended[key]:
            pts[pip] = (x, 0.50, 0.0)
            pts[dip] = (x, 0.42, 0.0)
            pts[tip] = (x, 0.35, 0.0)
        else:
            pts[pip] = (x, 0.60, 0.0)
            pts[dip] = (x, 0.64, 0.0)
            pts[tip] = (x, 0.66, 0.0)

    # Thumb chain (cmc, mcp, ip, tip).
    pts[1] = (0.42, 0.82, 0.0)
    pts[2] = (0.38, 0.74, 0.0)
    pts[3] = (0.35, 0.66, 0.0)
    pts[4] = (thumb_tip[0], thumb_tip[1], 0.0)

    assert all(p is not None for p in pts)
    return HandLandmarks.from_normalised(pts, "Right", 0.95)  # type: ignore[arg-type]
