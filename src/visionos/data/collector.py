"""Dataset collection utility for future ML training.

Records flattened 63-D hand-landmark vectors with a class label into a CSV file
that downstream training scripts (CNN / MLP / LSTM) can consume directly. The
schema is stable and documented by :meth:`MLBackend.feature_names`, so a model
trained on this output can later be wired into the gesture pipeline with no
changes to the capture format.

Interactive capture (label a live gesture by holding its number key)::

    python -m visionos.data.collector --label left_click --out datasets/raw.csv
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import List, Optional

from visionos.core.landmark import HandLandmarks
from visionos.gestures.ml.model import MLBackend
from visionos.utils.exceptions import DatasetError
from visionos.utils.logger import get_logger

logger = get_logger("data.collector")


class DatasetCollector:
    """Appends labelled landmark samples to a CSV file.

    The file is opened in append mode so multiple sessions accumulate into one
    dataset. A header row is written only when the file is first created.
    """

    def __init__(self, output_path: Path) -> None:
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._count = 0
        self._ensure_header()

    def _ensure_header(self) -> None:
        if self.output_path.exists() and self.output_path.stat().st_size > 0:
            return
        try:
            with self.output_path.open("w", newline="", encoding="utf-8") as fh:
                csv.writer(fh).writerow(["label", *MLBackend.feature_names()])
        except OSError as exc:
            raise DatasetError(f"Could not initialise dataset: {exc}") from exc

    def add_sample(self, label: str, hand: HandLandmarks) -> None:
        """Append one labelled sample (label + 63 landmark features)."""
        row: List[object] = [label, *hand.as_flat_vector()]
        try:
            with self.output_path.open("a", newline="", encoding="utf-8") as fh:
                csv.writer(fh).writerow(row)
        except OSError as exc:
            raise DatasetError(f"Could not append sample: {exc}") from exc
        self._count += 1

    @property
    def sample_count(self) -> int:
        return self._count


def _interactive_capture(label: str, out: Path, camera_index: int) -> None:  # pragma: no cover
    """Live capture loop: hold SPACE to record frames of ``label``."""
    import cv2

    from visionos.core.hand_tracker import HandTracker, TrackerConfig

    collector = DatasetCollector(out)
    cap = cv2.VideoCapture(camera_index)
    logger.info("Hold SPACE to record '%s'; press Q to quit.", label)

    with HandTracker(TrackerConfig()) as tracker:
        while cap.isOpened():
            ok, frame = cap.read()
            if not ok:
                break
            frame = cv2.flip(frame, 1)
            hands = tracker.process(frame)
            recording = False
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord(" ") and hands:
                collector.add_sample(label, hands[0])
                recording = True
            colour = (0, 0, 255) if recording else (0, 200, 0)
            cv2.putText(
                frame, f"{label}: {collector.sample_count} samples",
                (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, colour, 2,
            )
            cv2.imshow("Dataset Collector", frame)

    cap.release()
    cv2.destroyAllWindows()
    logger.info("Captured %d samples → %s", collector.sample_count, out)


def main() -> None:
    parser = argparse.ArgumentParser(description="VisionOS dataset collector")
    parser.add_argument("--label", required=True, help="Gesture class label")
    parser.add_argument("--out", type=Path, default=Path("datasets/landmarks.csv"))
    parser.add_argument("--camera", type=int, default=0)
    args = parser.parse_args()
    _interactive_capture(args.label, args.out, args.camera)


if __name__ == "__main__":
    main()
