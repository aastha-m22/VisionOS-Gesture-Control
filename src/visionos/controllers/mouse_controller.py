"""Cursor and click control via PyAutoGUI.

The mouse controller owns cursor concerns end to end: it maps the normalised
fingertip position into screen space (with an edge dead-band so the user can
reach screen corners without moving their hand off camera), applies One Euro
smoothing for the precision/responsiveness trade-off, and exposes click, drag
and scroll primitives.
"""

from __future__ import annotations

import time
from typing import Optional

from visionos.controllers.base import BaseController
from visionos.core.smoothing import OneEuroConfig, PointSmoother

try:
    import pyautogui

    pyautogui.FAILSAFE = False  # corner-hit abort is disruptive for gesture use
    pyautogui.PAUSE = 0.0
    _HAS_PYAUTOGUI = True
except Exception:  # pragma: no cover - headless environment
    pyautogui = None  # type: ignore[assignment]
    _HAS_PYAUTOGUI = False


class MouseController(BaseController):
    """Maps normalised hand coordinates to smoothed OS cursor actions."""

    name = "mouse"

    def __init__(
        self,
        sensitivity: float = 1.6,
        margin: float = 0.12,
        smoothing: Optional[OneEuroConfig] = None,
    ) -> None:
        super().__init__()
        self.sensitivity = sensitivity
        self.margin = margin
        self._smoother = PointSmoother(smoothing)
        self._dragging = False
        if not _HAS_PYAUTOGUI:
            self._disable("pyautogui unavailable (headless display)")
            self.screen_w, self.screen_h = 1920, 1080
        else:
            self.screen_w, self.screen_h = pyautogui.size()

    # --- configuration ----------------------------------------------------

    def update_smoothing(self, config: OneEuroConfig, sensitivity: float) -> None:
        self._smoother.update_config(config)
        self.sensitivity = sensitivity

    def _map_to_screen(self, nx: float, ny: float) -> tuple[float, float]:
        """Map normalised [0,1] coords to screen pixels with an edge dead-band.

        The active region is the central ``1 - 2*margin`` box; positions inside
        it are linearly stretched to cover the full screen and a sensitivity
        gain is applied around the centre.
        """
        span = max(1.0 - 2.0 * self.margin, 1e-3)
        mx = min(max((nx - self.margin) / span, 0.0), 1.0)
        my = min(max((ny - self.margin) / span, 0.0), 1.0)
        # Apply sensitivity as gain about the centre (0.5).
        mx = 0.5 + (mx - 0.5) * self.sensitivity
        my = 0.5 + (my - 0.5) * self.sensitivity
        mx = min(max(mx, 0.0), 1.0)
        my = min(max(my, 0.0), 1.0)
        return mx * self.screen_w, my * self.screen_h

    # --- actions ----------------------------------------------------------

    def move(self, nx: float, ny: float, timestamp: Optional[float] = None) -> None:
        if not self.available:
            return
        ts = timestamp if timestamp is not None else time.perf_counter()
        sx, sy = self._map_to_screen(nx, ny)
        smooth_x, smooth_y = self._smoother.smooth(sx, sy, ts)
        pyautogui.moveTo(int(smooth_x), int(smooth_y), _pause=False)

    def left_click(self) -> None:
        if self.available:
            pyautogui.click()

    def right_click(self) -> None:
        if self.available:
            pyautogui.click(button="right")

    def double_click(self) -> None:
        if self.available:
            pyautogui.doubleClick()

    def scroll(self, amount: int) -> None:
        if self.available:
            pyautogui.scroll(amount)

    def begin_drag(self, nx: float, ny: float) -> None:
        if self.available and not self._dragging:
            sx, sy = self._map_to_screen(nx, ny)
            pyautogui.moveTo(int(sx), int(sy), _pause=False)
            pyautogui.mouseDown()
            self._dragging = True

    def update_drag(self, nx: float, ny: float, timestamp: Optional[float] = None) -> None:
        if self.available and self._dragging:
            self.move(nx, ny, timestamp)

    def end_drag(self) -> None:
        if self.available and self._dragging:
            pyautogui.mouseUp()
            self._dragging = False

    @property
    def is_dragging(self) -> bool:
        return self._dragging
