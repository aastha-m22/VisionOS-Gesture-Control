"""Gesture vocabulary and recognition result types."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from visionos.core.landmark import Point


class Gesture(str, Enum):
    """The complete set of gestures the system can recognise.

    Inheriting from ``str`` makes the values JSON-serialisable and trivially
    usable as dictionary keys in profile action-mappings.
    """

    NONE = "none"
    CURSOR_MOVE = "cursor_move"      # index finger only
    LEFT_CLICK = "left_click"        # thumb + index pinch
    RIGHT_CLICK = "right_click"      # thumb + middle pinch
    DOUBLE_CLICK = "double_click"    # rapid repeated pinch
    DRAG = "drag"                    # closed fist
    SCROLL = "scroll"                # index + middle extended together
    VOLUME = "volume"               # thumb + index spread (open palm context)
    BRIGHTNESS = "brightness"        # thumb + pinky spread
    SCREENSHOT = "screenshot"        # three fingers (index+middle+ring)
    PLAY_PAUSE = "play_pause"        # open palm, all fingers extended
    NEXT_TRACK = "next_track"        # swipe right (pinky only)
    PREV_TRACK = "prev_track"        # swipe left (thumb only)


# Gestures that should fire once per "press" rather than continuously.
DISCRETE_GESTURES = frozenset(
    {
        Gesture.LEFT_CLICK,
        Gesture.RIGHT_CLICK,
        Gesture.DOUBLE_CLICK,
        Gesture.SCREENSHOT,
        Gesture.PLAY_PAUSE,
        Gesture.NEXT_TRACK,
        Gesture.PREV_TRACK,
    }
)

# Gestures that act continuously while held.
CONTINUOUS_GESTURES = frozenset(
    {
        Gesture.CURSOR_MOVE,
        Gesture.DRAG,
        Gesture.SCROLL,
        Gesture.VOLUME,
        Gesture.BRIGHTNESS,
    }
)


@dataclass(frozen=True)
class GestureResult:
    """Outcome of classifying a single frame.

    Args:
        gesture: The recognised gesture (``Gesture.NONE`` if undecided).
        confidence: Recognition confidence in ``[0, 1]``.
        cursor: Normalised pointer position when relevant (index fingertip).
        magnitude: Auxiliary scalar — e.g. pinch distance for volume/brightness.
    """

    gesture: Gesture = Gesture.NONE
    confidence: float = 0.0
    cursor: Optional[Point] = None
    magnitude: float = 0.0

    @property
    def is_actionable(self) -> bool:
        return self.gesture is not Gesture.NONE
