"""Maps recognised gestures onto concrete OS actions.

The dispatcher is the single place that knows *what a gesture does*. It enforces
the discrete-vs-continuous distinction: discrete gestures (clicks, screenshot,
media keys) fire once on the rising edge of the gesture, while continuous
gestures (move, drag, scroll, volume, brightness) act every frame they are held.
Keeping this logic out of both the classifier and the controllers leaves each of
those single-responsibility.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from visionos.config.settings import AppConfig
from visionos.controllers.brightness_controller import BrightnessController
from visionos.controllers.media_controller import MediaController
from visionos.controllers.mouse_controller import MouseController
from visionos.controllers.screenshot_controller import ScreenshotController
from visionos.controllers.volume_controller import VolumeController
from visionos.gestures.gesture_types import DISCRETE_GESTURES, Gesture, GestureResult
from visionos.utils.logger import get_logger

logger = get_logger("app.dispatcher")

# Magnitude (hand-scale spread) window mapped onto a 0-100 control range.
_SPREAD_MIN, _SPREAD_MAX = 0.7, 2.2


def _spread_to_percent(magnitude: float) -> float:
    span = _SPREAD_MAX - _SPREAD_MIN
    pct = (magnitude - _SPREAD_MIN) / span * 100.0
    return max(0.0, min(pct, 100.0))


@dataclass
class DispatchResult:
    """What the dispatcher did this frame, for the dashboard to display."""

    action: str = ""
    volume: Optional[float] = None
    brightness: Optional[float] = None


class ActionDispatcher:
    """Translates :class:`GestureResult` into controller calls."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.mouse = MouseController(
            sensitivity=config.smoothing.sensitivity,
            margin=config.controls.cursor_margin,
            smoothing=config.smoothing.to_one_euro(),
        )
        self.volume = VolumeController()
        self.brightness = BrightnessController()
        self.media = MediaController()
        self.screenshot = ScreenshotController(config.controls.screenshot_dir)
        self._last_gesture = Gesture.NONE
        self._last_scroll = 0.0

    def reconfigure(self, config: AppConfig) -> None:
        """Apply edited settings without restarting (called from the UI)."""
        self.config = config
        self.mouse.update_smoothing(
            config.smoothing.to_one_euro(), config.smoothing.sensitivity
        )
        self.mouse.margin = config.controls.cursor_margin

    def _is_rising_edge(self, gesture: Gesture) -> bool:
        return gesture is not self._last_gesture

    def dispatch(self, result: GestureResult) -> DispatchResult:
        gesture = result.gesture
        cursor = result.cursor
        out = DispatchResult()
        now = time.perf_counter()

        # Drag must be released as soon as the fist opens.
        if self.mouse.is_dragging and gesture is not Gesture.DRAG:
            self.mouse.end_drag()

        rising = self._is_rising_edge(gesture)

        if gesture is Gesture.CURSOR_MOVE and cursor is not None:
            self.mouse.move(cursor.x, cursor.y)
            out.action = "Move"

        elif gesture is Gesture.DRAG and cursor is not None:
            if not self.mouse.is_dragging:
                self.mouse.begin_drag(cursor.x, cursor.y)
            else:
                self.mouse.update_drag(cursor.x, cursor.y)
            out.action = "Drag"

        elif gesture is Gesture.SCROLL and cursor is not None:
            # Scroll direction from vertical position relative to frame centre.
            if cursor.y < 0.4:
                self.mouse.scroll(self.config.controls.scroll_speed)
                out.action = "Scroll Up"
            elif cursor.y > 0.6:
                self.mouse.scroll(-self.config.controls.scroll_speed)
                out.action = "Scroll Down"

        elif gesture is Gesture.VOLUME:
            pct = _spread_to_percent(result.magnitude)
            self.volume.set_volume(pct)
            out.volume = pct
            out.action = f"Volume {pct:.0f}%"

        elif gesture is Gesture.BRIGHTNESS:
            pct = _spread_to_percent(result.magnitude)
            self.brightness.set_brightness(pct)
            out.brightness = pct
            out.action = f"Brightness {pct:.0f}%"

        elif gesture in DISCRETE_GESTURES and rising:
            out.action = self._dispatch_discrete(gesture)

        self._last_gesture = gesture
        # Always surface the current device levels for the dashboard bars.
        if out.volume is None and self.volume.available:
            out.volume = self.volume.current
        if out.brightness is None and self.brightness.available:
            out.brightness = self.brightness.current
        return out

    def _dispatch_discrete(self, gesture: Gesture) -> str:
        if gesture is Gesture.LEFT_CLICK:
            self.mouse.left_click()
            return "Left Click"
        if gesture is Gesture.RIGHT_CLICK:
            self.mouse.right_click()
            return "Right Click"
        if gesture is Gesture.DOUBLE_CLICK:
            self.mouse.double_click()
            return "Double Click"
        if gesture is Gesture.SCREENSHOT:
            path = self.screenshot.capture()
            return "Screenshot" if path else ""
        if gesture is Gesture.PLAY_PAUSE:
            return "Play/Pause" if self.media.play_pause() else ""
        if gesture is Gesture.NEXT_TRACK:
            return "Next Track" if self.media.next_track() else ""
        if gesture is Gesture.PREV_TRACK:
            return "Prev Track" if self.media.previous_track() else ""
        return ""
