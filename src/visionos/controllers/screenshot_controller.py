"""Screenshot capture with automatic timestamped filenames.

Uses ``mss`` when available (fast, multi-monitor) and falls back to PyAutoGUI.
Saved files follow ``visionos_YYYYmmdd_HHMMSS.png`` so a capture session sorts
chronologically by name.
"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from visionos.controllers.base import BaseController


class ScreenshotController(BaseController):
    """Captures the screen to a configurable directory with a cooldown."""

    name = "screenshot"

    def __init__(self, output_dir: str = "screenshots", cooldown: float = 1.5) -> None:
        super().__init__()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._cooldown = cooldown
        self._last_capture = 0.0
        self._backend = self._detect_backend()
        if self._backend is None:
            self._disable("no screenshot backend (mss/pyautogui) available")

    @staticmethod
    def _detect_backend() -> Optional[str]:
        try:
            import mss  # noqa: F401

            return "mss"
        except Exception:
            pass
        try:
            import pyautogui  # noqa: F401

            return "pyautogui"
        except Exception:
            return None

    def capture(self) -> Optional[Path]:
        """Capture a screenshot, respecting the cooldown.

        Returns:
            The saved file path, or ``None`` if skipped/unavailable.
        """
        now = time.perf_counter()
        if not self.available or now - self._last_capture < self._cooldown:
            return None
        self._last_capture = now

        filename = f"visionos_{datetime.now():%Y%m%d_%H%M%S}.png"
        path = self.output_dir / filename
        try:
            if self._backend == "mss":
                import mss

                with mss.mss() as sct:
                    sct.shot(output=str(path))
            else:
                import pyautogui

                pyautogui.screenshot().save(path)
        except Exception as exc:  # pragma: no cover
            self._log.error("Screenshot failed: %s", exc)
            return None

        self._log.info("Saved screenshot → %s", path)
        return path
