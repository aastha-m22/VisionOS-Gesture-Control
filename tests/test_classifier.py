"""Tests for the rule-based gesture recogniser and the stateful classifier."""

from __future__ import annotations

import time

import pytest

from tests.helpers import build_hand
from visionos.gestures import rules
from visionos.gestures.classifier import GestureClassifier, RuleBasedBackend
from visionos.gestures.gesture_types import Gesture
from visionos.gestures.rules import GestureThresholds

THR = GestureThresholds()


def test_index_only_is_cursor_move():
    hand = build_hand(True, False, False, False, thumb_tip=(0.45, 0.55))
    assert rules.detect(hand, THR).gesture is Gesture.CURSOR_MOVE


def test_thumb_index_pinch_is_left_click():
    hand = build_hand(True, False, False, False, thumb_tip=(0.42, 0.37))
    assert rules.detect(hand, THR).gesture is Gesture.LEFT_CLICK


def test_thumb_middle_pinch_is_right_click():
    hand = build_hand(False, True, False, False, thumb_tip=(0.52, 0.37))
    assert rules.detect(hand, THR).gesture is Gesture.RIGHT_CLICK


def test_closed_fist_is_drag():
    hand = build_hand(False, False, False, False, thumb_tip=(0.45, 0.60))
    assert rules.detect(hand, THR).gesture is Gesture.DRAG


def test_open_palm_is_play_pause():
    hand = build_hand(True, True, True, True, thumb_tip=(0.18, 0.45))
    assert rules.detect(hand, THR).gesture is Gesture.PLAY_PAUSE


def test_two_fingers_is_scroll():
    hand = build_hand(True, True, False, False, thumb_tip=(0.45, 0.55))
    assert rules.detect(hand, THR).gesture is Gesture.SCROLL


def test_three_fingers_is_screenshot():
    hand = build_hand(True, True, True, False, thumb_tip=(0.45, 0.55))
    assert rules.detect(hand, THR).gesture is Gesture.SCREENSHOT


def test_thumb_index_spread_is_volume():
    hand = build_hand(True, False, False, False, thumb_tip=(0.12, 0.42))
    result = rules.detect(hand, THR)
    assert result.gesture is Gesture.VOLUME
    assert result.magnitude > THR.spread


def test_fist_is_not_misread_as_pinch():
    # Regression: a fist's curled tips sit near the thumb; must NOT be a click.
    hand = build_hand(False, False, False, False, thumb_tip=(0.45, 0.62))
    assert rules.detect(hand, THR).gesture is not Gesture.LEFT_CLICK


def test_classifier_stabilises_flicker():
    clf = GestureClassifier(RuleBasedBackend(THR), stabilise_window=4)
    cursor = build_hand(True, False, False, False, thumb_tip=(0.45, 0.55))
    # Feed several cursor frames; modal result should be CURSOR_MOVE.
    last = None
    for _ in range(5):
        last = clf.classify(cursor)
    assert last.gesture is Gesture.CURSOR_MOVE


def test_classifier_promotes_double_click():
    clf = GestureClassifier(RuleBasedBackend(THR), stabilise_window=1, double_click_window=0.5)
    pinch = build_hand(True, False, False, False, thumb_tip=(0.42, 0.37))
    first = clf.classify(pinch)
    assert first.gesture is Gesture.LEFT_CLICK
    second = clf.classify(pinch)  # within the window → double click
    assert second.gesture is Gesture.DOUBLE_CLICK


def test_classifier_backend_hot_swap():
    clf = GestureClassifier(RuleBasedBackend(THR))
    new_backend = RuleBasedBackend(GestureThresholds(pinch=0.5))
    clf.set_backend(new_backend)
    assert clf.backend is new_backend


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
