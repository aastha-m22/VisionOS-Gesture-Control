"""Real-time heads-up dashboard rendered directly onto the camera frame.

Draws an information panel (FPS, confidence, current gesture/action, CPU and
memory), a scrolling gesture-history strip, a hand skeleton, and contextual
volume/brightness bars. Everything is drawn with OpenCV primitives so there is
no extra GUI dependency and the overlay stays perfectly in sync with the video.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Optional

import cv2
import numpy as np

from visionos.core.landmark import HandLandmarks
from visionos.gestures.gesture_types import Gesture
from visionos.ui.themes import Theme, get_theme
from visionos.utils.metrics import MetricsSnapshot

_FONT = cv2.FONT_HERSHEY_SIMPLEX

# MediaPipe hand-skeleton connections (tip ↔ joint chains).
_CONNECTIONS = (
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
)


@dataclass
class DashboardState:
    """Snapshot of everything the dashboard needs to render one frame."""

    metrics: MetricsSnapshot
    gesture: Gesture
    action: str
    confidence: float
    volume: Optional[float] = None
    brightness: Optional[float] = None


class Dashboard:
    """Stateful renderer; keeps the rolling gesture history between frames."""

    def __init__(self, theme: str = "dark", history_length: int = 8) -> None:
        self.theme: Theme = get_theme(theme)
        self._history: Deque[str] = deque(maxlen=history_length)

    def set_theme(self, name: str) -> None:
        self.theme = get_theme(name)

    def record_gesture(self, gesture: Gesture) -> None:
        label = gesture.value
        if gesture is not Gesture.NONE and (not self._history or self._history[-1] != label):
            self._history.append(label)

    # --- drawing helpers --------------------------------------------------

    def _panel(self, frame: "np.ndarray", x: int, y: int, w: int, h: int, alpha: float = 0.55) -> None:
        overlay = frame.copy()
        cv2.rectangle(overlay, (x, y), (x + w, y + h), self.theme.panel, -1)
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        cv2.rectangle(frame, (x, y), (x + w, y + h), self.theme.accent, 1)

    def _text(self, frame, txt, x, y, colour=None, scale=0.5, thick=1) -> None:
        cv2.putText(frame, txt, (x, y), _FONT, scale, colour or self.theme.text, thick, cv2.LINE_AA)

    def _bar(self, frame, x, y, w, h, pct, colour) -> None:
        cv2.rectangle(frame, (x, y), (x + w, y + h), self.theme.text_dim, 1)
        fill = int(w * max(0.0, min(pct, 100.0)) / 100.0)
        cv2.rectangle(frame, (x, y), (x + fill, y + h), colour, -1)

    # --- public API -------------------------------------------------------

    def draw_skeleton(self, frame: "np.ndarray", hand: HandLandmarks) -> None:
        h, w = frame.shape[:2]
        pts = [(int(p.x * w), int(p.y * h)) for p in hand.points]
        for a, b in _CONNECTIONS:
            cv2.line(frame, pts[a], pts[b], self.theme.skeleton, 2, cv2.LINE_AA)
        for px, py in pts:
            cv2.circle(frame, (px, py), 3, self.theme.accent, -1, cv2.LINE_AA)

    def render(self, frame: "np.ndarray", state: DashboardState) -> "np.ndarray":
        h, w = frame.shape[:2]
        m = state.metrics

        # --- main metrics panel (top-left) --------------------------------
        self._panel(frame, 12, 12, 250, 150)
        self._text(frame, "VisionOS Gesture Control", 24, 36, self.theme.accent, 0.55, 1)

        fps_colour = self.theme.good if m.fps >= 20 else (self.theme.warn if m.fps >= 12 else self.theme.bad)
        self._text(frame, f"FPS:        {m.fps:5.1f}", 24, 62, fps_colour)
        conf_colour = self.theme.good if state.confidence >= 0.7 else self.theme.warn
        self._text(frame, f"Confidence: {state.confidence*100:4.0f}%", 24, 82, conf_colour)
        cpu = f"{m.cpu_percent:4.0f}%" if m.cpu_percent is not None else "  n/a"
        mem = f"{m.memory_mb:4.0f}MB" if m.memory_mb is not None else "  n/a"
        self._text(frame, f"CPU:        {cpu}", 24, 102, self.theme.text_dim)
        self._text(frame, f"Memory:     {mem}", 24, 122, self.theme.text_dim)
        self._text(frame, f"Gesture: {state.gesture.value}", 24, 146, self.theme.text)

        # --- active action banner (top-right) -----------------------------
        if state.action:
            bw = 230
            self._panel(frame, w - bw - 12, 12, bw, 46)
            self._text(frame, "ACTION", w - bw + 2, 32, self.theme.text_dim, 0.45)
            self._text(frame, state.action, w - bw + 2, 50, self.theme.accent, 0.6, 2)

        # --- gesture history strip (bottom-left) --------------------------
        if self._history:
            self._panel(frame, 12, h - 60, 320, 48)
            self._text(frame, "History:", 22, h - 38, self.theme.text_dim, 0.45)
            chips = "  ".join(list(self._history)[-5:])
            self._text(frame, chips, 22, h - 18, self.theme.text, 0.5)

        # --- contextual volume / brightness bars (right edge) -------------
        if state.volume is not None:
            self._text(frame, "VOL", w - 60, h - 150, self.theme.text_dim, 0.45)
            self._bar(frame, w - 60, h - 140, 24, 120, state.volume, self.theme.good)
            self._text(frame, f"{state.volume:3.0f}", w - 64, h - 12, self.theme.text, 0.45)
        if state.brightness is not None:
            self._text(frame, "BRT", w - 28, h - 150, self.theme.text_dim, 0.45)
            self._bar(frame, w - 28, h - 140, 24, 120, state.brightness, self.theme.warn)
            self._text(frame, f"{state.brightness:3.0f}", w - 32, h - 12, self.theme.text, 0.45)

        return frame
