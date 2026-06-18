"""Screen-brightness control via the ``screen-brightness-control`` package.

The library abstracts Windows, macOS and most Linux backends. It is optional;
when missing or when no controllable display is found the controller disables
itself gracefully.
"""

from __future__ import annotations

from typing import Optional

from visionos.controllers.base import BaseController

try:
    import screen_brightness_control as sbc

    _HAS_SBC = True
except Exception:  # pragma: no cover - optional dependency
    sbc = None  # type: ignore[assignment]
    _HAS_SBC = False


class BrightnessController(BaseController):
    """Sets primary-display brightness from a 0–100 percentage."""

    name = "brightness"

    def __init__(self) -> None:
        super().__init__()
        self._current = 50.0
        if not _HAS_SBC:
            self._disable("screen-brightness-control not installed")
            return
        try:
            levels = sbc.get_brightness()
            if levels:
                self._current = float(levels[0])
        except Exception as exc:  # pragma: no cover - no controllable display
            self._disable(f"no controllable display: {exc}")

    @property
    def current(self) -> float:
        return self._current

    def set_brightness(self, percent: float) -> None:
        percent = max(0.0, min(percent, 100.0))
        self._current = percent
        if self.available and sbc is not None:
            try:
                sbc.set_brightness(int(percent))
            except Exception as exc:  # pragma: no cover
                self._disable(f"runtime error: {exc}")
