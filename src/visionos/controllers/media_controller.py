"""Media transport control via the OS media keys.

PyAutoGUI exposes the multimedia scan-codes (``playpause``, ``nexttrack``,
``prevtrack``) which most desktop players and browsers honour. A short cooldown
prevents a held gesture from spamming track skips.
"""

from __future__ import annotations

import time

from visionos.controllers.base import BaseController

try:
    import pyautogui

    _HAS_PYAUTOGUI = True
except Exception:  # pragma: no cover - headless environment
    pyautogui = None  # type: ignore[assignment]
    _HAS_PYAUTOGUI = False


class MediaController(BaseController):
    """Sends multimedia key presses with debouncing."""

    name = "media"

    def __init__(self, cooldown: float = 0.8) -> None:
        super().__init__()
        self._cooldown = cooldown
        self._last_press = 0.0
        if not _HAS_PYAUTOGUI:
            self._disable("pyautogui unavailable")

    def _press(self, key: str) -> bool:
        now = time.perf_counter()
        if not self.available or now - self._last_press < self._cooldown:
            return False
        self._last_press = now
        pyautogui.press(key)
        self._log.info("media key: %s", key)
        return True

    def play_pause(self) -> bool:
        return self._press("playpause")

    def next_track(self) -> bool:
        return self._press("nexttrack")

    def previous_track(self) -> bool:
        return self._press("prevtrack")
