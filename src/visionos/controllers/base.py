"""Base class shared by every OS-level controller.

All controllers (mouse, volume, brightness, media, screenshot) follow the same
contract: they may be unavailable on a given platform, and callers must be able
to query availability rather than catching backend-specific exceptions. This is
the Liskov-substitutable base that lets the application treat every controller
uniformly.
"""

from __future__ import annotations

from abc import ABC
from typing import ClassVar

from visionos.utils.logger import get_logger


class BaseController(ABC):
    """Common availability/logging behaviour for controllers."""

    name: ClassVar[str] = "controller"

    def __init__(self) -> None:
        self._available = True
        self._log = get_logger(f"controllers.{self.name}")

    @property
    def available(self) -> bool:
        """Whether this controller can actually act on the current platform."""
        return self._available

    def _disable(self, reason: str) -> None:
        self._available = False
        self._log.warning("%s disabled: %s", self.name, reason)
