"""Placeholder for future gaze-based pointer control.

Intended design: a separate ``GazeEstimator`` produces a normalised screen
point from face/eye landmarks (e.g. MediaPipe FaceMesh iris landmarks), which is
*fused* with hand-based cursor control — gaze for coarse positioning, fingertip
for fine adjustment. The fused estimate would feed the same
``MouseController.move`` entry point used today, so no controller changes are
needed when this lands.
"""

from __future__ import annotations

from typing import Optional, Tuple

from visionos.utils.logger import get_logger

logger = get_logger("integrations.eye_tracking")


class GazeEstimator:
    """Stub gaze estimator. Returns ``None`` until implemented."""

    def __init__(self) -> None:
        self.enabled = False
        logger.debug("GazeEstimator stub created (not yet implemented)")

    def estimate(self, frame) -> Optional[Tuple[float, float]]:
        """Return a normalised (x, y) gaze point, or None if unavailable."""
        return None
