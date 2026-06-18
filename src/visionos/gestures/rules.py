"""Rule-based gesture detection.

Each gesture is expressed as a small, independently testable predicate over a
:class:`HandLandmarks` instance plus the tunable :class:`GestureThresholds`.
This keeps the recognition logic declarative and makes the rules easy to unit
test in isolation (see ``tests/test_classifier.py``).

The rules are intentionally ordered by specificity inside
:class:`RuleBasedBackend` so that, for example, a precise pinch is detected
before the more general "index finger up" cursor pose.
"""

from __future__ import annotations

from dataclasses import dataclass

from visionos.core.landmark import HandLandmarks, Landmark
from visionos.gestures.gesture_types import Gesture, GestureResult


@dataclass(frozen=True)
class GestureThresholds:
    """Distance/ratio thresholds controlling rule sensitivity.

    All distances are in hand-scale units (see ``HandLandmarks.hand_scale``) so
    they are invariant to how close the hand is to the camera.
    """

    pinch: float = 0.35          # thumb-fingertip distance counted as a pinch
    spread: float = 0.9          # distance counted as a deliberate spread
    fist_curl: float = 0.55      # max fingertip-to-palm distance for a fist


def _is_pinch(hand: HandLandmarks, tip: Landmark, thr: GestureThresholds) -> bool:
    return hand.normalised_distance(Landmark.THUMB_TIP, tip) < thr.pinch


def _is_fist(hand: HandLandmarks, thr: GestureThresholds) -> bool:
    extended = hand.fingers_extended()
    return not any(extended) and not hand.thumb_extended()


def _is_open_palm(hand: HandLandmarks) -> bool:
    return all(hand.fingers_extended()) and hand.thumb_extended()


def detect(hand: HandLandmarks, thr: GestureThresholds) -> GestureResult:
    """Classify a single hand pose into a :class:`GestureResult`.

    Returns the first matching rule by priority. The cursor position is always
    the index fingertip, so downstream cursor smoothing can run regardless of
    which gesture fired.
    """
    index_tip = hand[Landmark.INDEX_TIP]
    fingers = hand.fingers_extended()  # [index, middle, ring, pinky]
    index_up, middle_up, ring_up, pinky_up = fingers

    # --- fist → drag (checked first: a fist's curled tips sit near the thumb
    #     and would otherwise be misread as a pinch) -----------------------
    if _is_fist(hand, thr):
        return GestureResult(Gesture.DRAG, hand.score, hand.palm_center)

    # --- pinches (a pinch implies the pinched finger is extended) ----------
    if index_up and _is_pinch(hand, Landmark.INDEX_TIP, thr):
        return GestureResult(Gesture.LEFT_CLICK, hand.score, index_tip)
    if middle_up and _is_pinch(hand, Landmark.MIDDLE_TIP, thr):
        return GestureResult(Gesture.RIGHT_CLICK, hand.score, index_tip)

    # --- open palm → play / pause ----------------------------------------
    if _is_open_palm(hand):
        return GestureResult(Gesture.PLAY_PAUSE, hand.score, index_tip)

    # --- two fingers (index + middle) → scroll ----------------------------
    if index_up and middle_up and not ring_up and not pinky_up:
        return GestureResult(Gesture.SCROLL, hand.score, index_tip)

    # --- three fingers → screenshot --------------------------------------
    if index_up and middle_up and ring_up and not pinky_up:
        return GestureResult(Gesture.SCREENSHOT, hand.score, index_tip)

    # --- thumb + index spread → volume -----------------------------------
    spread_ti = hand.normalised_distance(Landmark.THUMB_TIP, Landmark.INDEX_TIP)
    if index_up and hand.thumb_extended() and not middle_up and spread_ti > thr.spread:
        return GestureResult(Gesture.VOLUME, hand.score, index_tip, spread_ti)

    # --- thumb + pinky spread → brightness -------------------------------
    spread_tp = hand.normalised_distance(Landmark.THUMB_TIP, Landmark.PINKY_TIP)
    if pinky_up and hand.thumb_extended() and not index_up and spread_tp > thr.spread:
        return GestureResult(Gesture.BRIGHTNESS, hand.score, index_tip, spread_tp)

    # --- single-finger swipes for media skip -----------------------------
    if pinky_up and not index_up and not middle_up and not ring_up:
        return GestureResult(Gesture.NEXT_TRACK, hand.score, index_tip)

    # --- index only → cursor move (lowest priority, most general) --------
    if index_up and not middle_up and not ring_up and not pinky_up:
        return GestureResult(Gesture.CURSOR_MOVE, hand.score, index_tip)

    return GestureResult(Gesture.NONE, 0.0, index_tip)
