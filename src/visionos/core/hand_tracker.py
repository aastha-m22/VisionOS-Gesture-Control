"""Typed wrapper around MediaPipe hand tracking, robust across versions.

This is the only module in the project that imports MediaPipe directly. Every
other layer consumes the framework-agnostic :class:`HandLandmarks` value object,
so the tracking backend can be swapped without touching gesture or controller
code (Dependency Inversion).

MediaPipe shipped two incompatible Python APIs:

* the **legacy** ``mediapipe.solutions.hands`` API (<= 0.10.14), and
* the newer **Tasks** API ``mediapipe.tasks.python.vision.HandLandmarker``
  (recent builds dropped ``solutions`` entirely).

To make the project run on *whatever* MediaPipe a user happens to have, this
module detects which API is available and adapts. The legacy API is preferred
because it needs no model download; if only the Tasks API is present, the
landmark model bundle is fetched once and cached under
``~/.cache/visionos/``.
"""

from __future__ import annotations

import os
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import numpy as np

from visionos.core.landmark import HandLandmarks
from visionos.utils.exceptions import TrackingError
from visionos.utils.logger import get_logger

logger = get_logger("core.hand_tracker")

try:
    import mediapipe as mp

    _HAS_MEDIAPIPE = True
except Exception as exc:  # pragma: no cover - environment dependent
    mp = None  # type: ignore[assignment]
    _HAS_MEDIAPIPE = False
    logger.error("MediaPipe import failed: %s", exc)

# Official Google-hosted landmark bundle, used only by the Tasks-API fallback.
_TASK_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
_CACHE_DIR = Path(os.path.expanduser("~")) / ".cache" / "visionos"


@dataclass(frozen=True)
class TrackerConfig:
    """Configuration for the hand-tracking backend."""

    max_hands: int = 1
    detection_confidence: float = 0.7
    tracking_confidence: float = 0.6
    model_complexity: int = 1


def _has_legacy_api() -> bool:
    return (
        _HAS_MEDIAPIPE
        and hasattr(mp, "solutions")
        and hasattr(mp.solutions, "hands")
    )


def _has_tasks_api() -> bool:
    try:
        from mediapipe.tasks import python  # noqa: F401
        from mediapipe.tasks.python import vision  # noqa: F401

        return True
    except Exception:
        return False


class _LegacyBackend:
    """Adapter for ``mediapipe.solutions.hands`` (no model download needed)."""

    def __init__(self, config: TrackerConfig) -> None:
        self._hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=config.max_hands,
            min_detection_confidence=config.detection_confidence,
            min_tracking_confidence=config.tracking_confidence,
            model_complexity=config.model_complexity,
        )
        logger.info("Using MediaPipe legacy solutions API")

    def process(self, frame_rgb: "np.ndarray") -> List[HandLandmarks]:
        result = self._hands.process(frame_rgb)
        hands: List[HandLandmarks] = []
        if not result.multi_hand_landmarks:
            return hands
        handedness_list = result.multi_handedness or []
        for idx, landmarks in enumerate(result.multi_hand_landmarks):
            coords = [(lm.x, lm.y, lm.z) for lm in landmarks.landmark]
            label, score = "Unknown", 0.0
            if idx < len(handedness_list):
                cls = handedness_list[idx].classification[0]
                label, score = cls.label, cls.score
            hands.append(HandLandmarks.from_normalised(coords, label, score))
        return hands

    def close(self) -> None:
        try:
            self._hands.close()
        except Exception as exc:  # pragma: no cover
            logger.debug("Error closing MediaPipe graph: %s", exc)


class _TasksBackend:
    """Adapter for the modern ``HandLandmarker`` Tasks API."""

    def __init__(self, config: TrackerConfig) -> None:
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision

        model_path = self._ensure_model()
        options = vision.HandLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=str(model_path)),
            num_hands=config.max_hands,
            min_hand_detection_confidence=config.detection_confidence,
            min_tracking_confidence=config.tracking_confidence,
            running_mode=vision.RunningMode.IMAGE,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)
        logger.info("Using MediaPipe Tasks API (HandLandmarker)")

    @staticmethod
    def _ensure_model() -> Path:
        path = _CACHE_DIR / "hand_landmarker.task"
        if path.exists():
            return path
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        logger.info("Downloading hand-landmark model (one-time) ...")
        try:
            urllib.request.urlretrieve(_TASK_MODEL_URL, path)
        except Exception as exc:
            raise TrackingError(
                "Could not download the hand-landmark model and the legacy "
                "MediaPipe API is unavailable. Either connect to the internet "
                "once, or install the legacy API with "
                '`pip install "mediapipe<0.10.15"`.'
            ) from exc
        return path

    def process(self, frame_rgb: "np.ndarray") -> List[HandLandmarks]:
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        result = self._landmarker.detect(image)
        hands: List[HandLandmarks] = []
        if not result.hand_landmarks:
            return hands
        handedness_list = result.handedness or []
        for idx, landmarks in enumerate(result.hand_landmarks):
            coords = [(lm.x, lm.y, lm.z) for lm in landmarks]
            label, score = "Unknown", 0.0
            if idx < len(handedness_list) and handedness_list[idx]:
                cat = handedness_list[idx][0]
                label, score = cat.category_name, cat.score
            hands.append(HandLandmarks.from_normalised(coords, label, score))
        return hands

    def close(self) -> None:
        try:
            self._landmarker.close()
        except Exception as exc:  # pragma: no cover
            logger.debug("Error closing HandLandmarker: %s", exc)


class HandTracker:
    """Detects hands in BGR frames and yields :class:`HandLandmarks`.

    Used as a context manager so the underlying graph is always released::

        with HandTracker(TrackerConfig()) as tracker:
            hands = tracker.process(frame)
    """

    def __init__(self, config: Optional[TrackerConfig] = None) -> None:
        if not _HAS_MEDIAPIPE:
            raise TrackingError(
                "MediaPipe is not installed. Run `pip install mediapipe`."
            )
        self.config = config or TrackerConfig()
        if _has_legacy_api():
            self._backend = _LegacyBackend(self.config)
        elif _has_tasks_api():
            self._backend = _TasksBackend(self.config)
        else:  # pragma: no cover - exotic broken install
            raise TrackingError(
                "This MediaPipe build exposes neither the legacy `solutions` "
                "API nor the Tasks API. Install a supported version with "
                '`pip install "mediapipe<0.10.15"`.'
            )
        logger.info("HandTracker ready (max_hands=%d)", self.config.max_hands)

    def __enter__(self) -> "HandTracker":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def process(self, frame_bgr: "np.ndarray") -> List[HandLandmarks]:
        """Run detection on a single BGR frame.

        Returns a (possibly empty) list of detected hands. Any backend error is
        contained here and logged, returning an empty list so a single bad frame
        never crashes the capture loop.
        """
        import cv2

        try:
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            frame_rgb = np.ascontiguousarray(frame_rgb)
            return self._backend.process(frame_rgb)
        except Exception as exc:  # pragma: no cover - runtime robustness
            logger.warning("Hand tracking failed on a frame: %s", exc)
            return []

    def close(self) -> None:
        self._backend.close()
