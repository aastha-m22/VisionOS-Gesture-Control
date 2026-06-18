"""Placeholder for future learned gesture models.

The architecture deliberately routes all recognition through the
:class:`~visionos.gestures.classifier.GestureBackend` interface so that a
trained CNN (single-frame pose), LSTM/Transformer (temporal gesture), or other
model can be dropped in without changing any caller. This module documents the
intended contract and provides a stub that can be wired up once a model is
trained from data captured by ``visionos.data.collector``.

Planned training pipeline (see ``docs/ARCHITECTURE.md``):
    1. Collect labelled landmark sequences with the dataset collector.
    2. Train an MLP/CNN for static poses or an LSTM/Transformer for dynamic
       gestures, exporting to ONNX.
    3. Implement ``MLBackend.classify`` to run inference and map the argmax
       class to a :class:`~visionos.gestures.gesture_types.Gesture`.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from visionos.core.landmark import HandLandmarks
from visionos.gestures.gesture_types import Gesture, GestureResult
from visionos.utils.logger import get_logger

logger = get_logger("gestures.ml.model")


class MLBackend:
    """Stub learned backend. Not yet wired into the pipeline.

    The method signatures match :class:`GestureBackend` so that, once a model is
    available, ``classifier.GestureClassifier`` can accept an ``MLBackend``
    instance with no other code changes.
    """

    def __init__(self, model_path: Optional[Path] = None) -> None:
        self.model_path = model_path
        self._session = None  # would hold an onnxruntime.InferenceSession
        if model_path is not None:
            logger.info("MLBackend created (model not yet loaded): %s", model_path)

    def load(self) -> None:
        """Load weights into memory. Intentionally unimplemented."""
        raise NotImplementedError(
            "Learned gesture model not yet trained. Use the dataset collector "
            "to gather samples, train a model, then implement this method."
        )

    def classify(self, hand: HandLandmarks) -> GestureResult:  # pragma: no cover
        """Return a prediction. Currently a no-op returning NONE."""
        _ = hand.as_flat_vector()  # the 63-D feature vector a model would consume
        return GestureResult(Gesture.NONE, 0.0)

    @staticmethod
    def feature_names() -> List[str]:
        """Names of the 63 input features (x/y/z per landmark)."""
        axes = ("x", "y", "z")
        return [f"lm{i}_{a}" for i in range(21) for a in axes]
