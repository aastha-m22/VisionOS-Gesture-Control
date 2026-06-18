"""Gesture classification orchestrator.

Responsibilities split across two collaborators:

* :class:`GestureBackend` — a strategy interface that maps a *single frame* to a
  raw :class:`GestureResult`. ``RuleBasedBackend`` implements it today; a learned
  ``MLBackend`` can replace it later (Open/Closed principle).
* :class:`GestureClassifier` — wraps a backend with *temporal* logic that no
  single frame can provide: majority-vote stabilisation against flicker, and
  double-click detection from rapid successive left-click pinches.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections import Counter, deque
from typing import Deque, Optional

from visionos.core.landmark import HandLandmarks
from visionos.gestures import rules
from visionos.gestures.gesture_types import Gesture, GestureResult
from visionos.gestures.rules import GestureThresholds
from visionos.utils.logger import get_logger

logger = get_logger("gestures.classifier")


class GestureBackend(ABC):
    """Strategy interface: frame → raw gesture."""

    @abstractmethod
    def classify(self, hand: HandLandmarks) -> GestureResult:
        """Classify a single hand pose without temporal context."""


class RuleBasedBackend(GestureBackend):
    """Deterministic backend driven by :mod:`visionos.gestures.rules`."""

    def __init__(self, thresholds: Optional[GestureThresholds] = None) -> None:
        self.thresholds = thresholds or GestureThresholds()

    def classify(self, hand: HandLandmarks) -> GestureResult:
        return rules.detect(hand, self.thresholds)


class GestureClassifier:
    """Stabilised, stateful classifier built on top of a frame backend.

    Args:
        backend: The per-frame recognition strategy.
        stabilise_window: Number of recent frames used for majority voting; a
            larger window reduces flicker at the cost of a little latency.
        double_click_window: Maximum seconds between two left-click pinches for
            them to be merged into a double click.
    """

    def __init__(
        self,
        backend: Optional[GestureBackend] = None,
        stabilise_window: int = 4,
        double_click_window: float = 0.4,
    ) -> None:
        self.backend = backend or RuleBasedBackend()
        self._history: Deque[Gesture] = deque(maxlen=stabilise_window)
        self._double_click_window = double_click_window
        self._last_click_time = 0.0

    def set_backend(self, backend: GestureBackend) -> None:
        """Hot-swap the recognition strategy (e.g. rules → ML)."""
        logger.info("Gesture backend switched to %s", type(backend).__name__)
        self.backend = backend

    def _stabilise(self, gesture: Gesture) -> Gesture:
        """Return the modal gesture across the recent window to reduce flicker."""
        self._history.append(gesture)
        if not self._history:
            return gesture
        most_common, _ = Counter(self._history).most_common(1)[0]
        return most_common

    def classify(self, hand: HandLandmarks) -> GestureResult:
        raw = self.backend.classify(hand)
        stable = self._stabilise(raw.gesture)

        # Promote a left-click to a double-click if two land within the window.
        if stable is Gesture.LEFT_CLICK:
            now = time.perf_counter()
            if now - self._last_click_time < self._double_click_window:
                self._last_click_time = 0.0  # consume, avoid triple-trigger
                return GestureResult(
                    Gesture.DOUBLE_CLICK, raw.confidence, raw.cursor, raw.magnitude
                )
            self._last_click_time = now

        if stable is not raw.gesture:
            return GestureResult(stable, raw.confidence, raw.cursor, raw.magnitude)
        return raw

    def reset(self) -> None:
        self._history.clear()
        self._last_click_time = 0.0
