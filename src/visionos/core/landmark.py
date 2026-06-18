"""Hand-landmark data structures and geometry helpers.

MediaPipe returns 21 normalised landmarks per hand. Rather than passing raw
proto objects around the codebase, we convert them once into a typed,
immutable :class:`HandLandmarks` value object exposing the geometric queries
(finger extension, inter-point distance, palm centre, ...) that gesture rules
need. Keeping this geometry in one place keeps the gesture layer declarative.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import IntEnum
from typing import List, Sequence, Tuple


class Landmark(IntEnum):
    """Semantic names for the 21 MediaPipe hand-landmark indices."""

    WRIST = 0
    THUMB_CMC = 1
    THUMB_MCP = 2
    THUMB_IP = 3
    THUMB_TIP = 4
    INDEX_MCP = 5
    INDEX_PIP = 6
    INDEX_DIP = 7
    INDEX_TIP = 8
    MIDDLE_MCP = 9
    MIDDLE_PIP = 10
    MIDDLE_DIP = 11
    MIDDLE_TIP = 12
    RING_MCP = 13
    RING_PIP = 14
    RING_DIP = 15
    RING_TIP = 16
    PINKY_MCP = 17
    PINKY_PIP = 18
    PINKY_DIP = 19
    PINKY_TIP = 20


# Tip / pip pairs used to decide whether a finger is extended.
_FINGER_TIPS = (
    Landmark.INDEX_TIP,
    Landmark.MIDDLE_TIP,
    Landmark.RING_TIP,
    Landmark.PINKY_TIP,
)
_FINGER_PIPS = (
    Landmark.INDEX_PIP,
    Landmark.MIDDLE_PIP,
    Landmark.RING_PIP,
    Landmark.PINKY_PIP,
)


@dataclass(frozen=True)
class Point:
    """A single normalised landmark coordinate in [0, 1] (plus depth ``z``)."""

    x: float
    y: float
    z: float = 0.0

    def distance_to(self, other: "Point") -> float:
        """2-D Euclidean distance (depth ignored, sufficient for gestures)."""
        return math.hypot(self.x - other.x, self.y - other.y)


@dataclass(frozen=True)
class HandLandmarks:
    """An immutable set of 21 landmarks for a single detected hand.

    Args:
        points: Exactly 21 :class:`Point` instances in MediaPipe order.
        handedness: ``"Left"`` or ``"Right"`` as reported by MediaPipe.
        score: Detection confidence in ``[0, 1]``.
    """

    points: Tuple[Point, ...]
    handedness: str
    score: float

    def __post_init__(self) -> None:
        if len(self.points) != 21:
            raise ValueError(f"Expected 21 landmarks, got {len(self.points)}")

    @classmethod
    def from_normalised(
        cls,
        coords: Sequence[Tuple[float, float, float]],
        handedness: str,
        score: float,
    ) -> "HandLandmarks":
        points = tuple(Point(x, y, z) for x, y, z in coords)
        return cls(points=points, handedness=handedness, score=score)

    def __getitem__(self, landmark: Landmark) -> Point:
        return self.points[int(landmark)]

    # --- geometric queries -------------------------------------------------

    def distance(self, a: Landmark, b: Landmark) -> float:
        """Normalised distance between two landmarks."""
        return self[a].distance_to(self[b])

    @property
    def hand_scale(self) -> float:
        """A scale-invariant reference length (wrist to middle MCP).

        Pinch/spread thresholds are divided by this so they behave consistently
        whether the hand is near or far from the camera.
        """
        scale = self.distance(Landmark.WRIST, Landmark.MIDDLE_MCP)
        return max(scale, 1e-6)

    def normalised_distance(self, a: Landmark, b: Landmark) -> float:
        """Distance between two landmarks expressed in hand-scale units."""
        return self.distance(a, b) / self.hand_scale

    def fingers_extended(self) -> List[bool]:
        """Boolean extension state for [index, middle, ring, pinky].

        A finger is considered extended when its tip is higher on the image
        (smaller ``y``) than its PIP joint by a small margin.
        """
        margin = 0.02
        return [
            self[tip].y < self[pip].y - margin
            for tip, pip in zip(_FINGER_TIPS, _FINGER_PIPS)
        ]

    def thumb_extended(self) -> bool:
        """Whether the thumb is splayed away from the index finger."""
        return self.normalised_distance(Landmark.THUMB_TIP, Landmark.INDEX_MCP) > 0.7

    @property
    def palm_center(self) -> Point:
        """Approximate palm centre, averaging wrist and the four MCP joints."""
        ids = (
            Landmark.WRIST,
            Landmark.INDEX_MCP,
            Landmark.MIDDLE_MCP,
            Landmark.RING_MCP,
            Landmark.PINKY_MCP,
        )
        x = sum(self[i].x for i in ids) / len(ids)
        y = sum(self[i].y for i in ids) / len(ids)
        return Point(x, y)

    def as_flat_vector(self) -> List[float]:
        """Flatten to ``[x0, y0, z0, x1, ...]`` for dataset/ML consumption."""
        flat: List[float] = []
        for p in self.points:
            flat.extend((p.x, p.y, p.z))
        return flat
