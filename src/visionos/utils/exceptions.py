"""Domain-specific exception hierarchy for VisionOS Gesture Control.

Centralising exceptions lets every layer raise (and callers catch) errors with
clear semantics instead of leaking low-level library exceptions across module
boundaries. Each subsystem owns a narrow exception type derived from
:class:`VisionOSError`.
"""

from __future__ import annotations


class VisionOSError(Exception):
    """Base class for every error raised inside the application."""


class CameraError(VisionOSError):
    """Raised when the webcam cannot be opened or a frame cannot be read."""


class ConfigError(VisionOSError):
    """Raised when configuration or a user profile fails to load or validate."""


class ControllerError(VisionOSError):
    """Raised when an OS-level controller (mouse, volume, ...) fails."""


class TrackingError(VisionOSError):
    """Raised when the hand-tracking backend fails irrecoverably."""


class DatasetError(VisionOSError):
    """Raised when dataset collection or serialisation fails."""
