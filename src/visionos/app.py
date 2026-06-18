"""Application orchestrator: the real-time capture -> recognise -> act loop.

:class:`VisionOSApp` owns the lifecycle and wires the layers together but holds
no domain logic itself. The loop is defensively written: a failure in any single
frame is logged and skipped rather than crashing the whole session, the settings
editor runs on the main thread (Tkinter is not thread-safe), and a ``dry_run``
mode lets the pipeline run end-to-end without actuating the real mouse/keyboard.
"""

from __future__ import annotations

import time
from typing import Callable, Iterator, Optional

from visionos.config.settings import AppConfig, ConfigManager
from visionos.controllers.dispatcher import ActionDispatcher
from visionos.core.hand_tracker import HandTracker, TrackerConfig
from visionos.gestures.classifier import GestureClassifier, RuleBasedBackend
from visionos.gestures.gesture_types import Gesture
from visionos.ui.dashboard import Dashboard, DashboardState
from visionos.utils.exceptions import CameraError, VisionOSError
from visionos.utils.logger import get_logger
from visionos.utils.metrics import PerformanceMonitor

logger = get_logger("app")

_WINDOW = "VisionOS Gesture Control"
_MAX_READ_FAILURES = 30  # consecutive bad reads before giving up


class VisionOSApp:
    """End-to-end gesture-control application."""

    def __init__(self, config: Optional[AppConfig] = None, dry_run: bool = False) -> None:
        self.config = config or AppConfig()
        self.dry_run = dry_run
        self._tracker_cfg = TrackerConfig(
            max_hands=self.config.tracking.max_hands,
            detection_confidence=self.config.tracking.detection_confidence,
            tracking_confidence=self.config.tracking.tracking_confidence,
            model_complexity=self.config.tracking.model_complexity,
        )
        self.classifier = GestureClassifier(
            RuleBasedBackend(self.config.thresholds.to_thresholds())
        )
        self.dispatcher = ActionDispatcher(self.config)
        if dry_run:
            self._disarm_controllers()
        self.dashboard = Dashboard(self.config.ui.theme, self.config.ui.history_length)
        self.monitor = PerformanceMonitor()
        self._paused = False
        self._running = False

    def _disarm_controllers(self) -> None:
        """Disable every OS controller so nothing is actuated (dry-run/preview)."""
        for ctrl in (
            self.dispatcher.mouse,
            self.dispatcher.volume,
            self.dispatcher.brightness,
            self.dispatcher.media,
            self.dispatcher.screenshot,
        ):
            ctrl._disable("dry-run mode")
        logger.info("Dry-run: OS actions are disabled (dashboard preview only)")

    # --- camera helpers ---------------------------------------------------

    def _open_camera(self):
        import cv2

        cap = cv2.VideoCapture(self.config.camera.index)
        if not cap.isOpened():
            raise CameraError(
                f"Cannot open camera index {self.config.camera.index}. "
                "Check the camera is connected and not in use, or try "
                "`--camera 1`."
            )
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.camera.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.camera.height)
        logger.info("Camera %d opened", self.config.camera.index)
        return cap

    def _webcam_frames(self, cap) -> Iterator["object"]:
        """Yield frames from an OpenCV capture, tolerating transient hiccups."""
        import cv2

        failures = 0
        while cap.isOpened():
            ok, frame = cap.read()
            if not ok:
                failures += 1
                if failures >= _MAX_READ_FAILURES:
                    raise CameraError("Camera stopped returning frames")
                time.sleep(0.01)
                continue
            failures = 0
            if self.config.camera.flip_horizontal:
                frame = cv2.flip(frame, 1)
            yield frame

    # --- main loop --------------------------------------------------------

    def run(self) -> None:
        """Start the blocking webcam loop until the user quits."""
        import cv2

        cap = self._open_camera()
        try:
            self._loop(self._webcam_frames(cap), headless=False)
        finally:
            cap.release()
            try:
                cv2.destroyAllWindows()
            except Exception:  # pragma: no cover
                pass
            logger.info("Application stopped")

    def run_frames(
        self,
        frames: Iterator["object"],
        *,
        headless: bool = False,
        max_frames: Optional[int] = None,
    ) -> int:
        """Drive the pipeline from any frame iterator (simulate / self-test).

        Returns the number of frames processed. ``headless`` skips the GUI
        window so it runs on machines with no display.
        """
        return self._loop(frames, headless=headless, max_frames=max_frames)

    def _loop(
        self,
        frames: Iterator["object"],
        *,
        headless: bool,
        max_frames: Optional[int] = None,
    ) -> int:
        import cv2

        self._running = True
        processed = 0
        logger.info(
            "Starting loop. Keys: [q]uit  [p]ause  [s]ettings  [1/2/3] profiles"
        )
        try:
            with HandTracker(self._tracker_cfg) as tracker:
                for frame in frames:
                    if not self._running:
                        break
                    self.monitor.tick()
                    try:
                        frame = self._process_frame(tracker, frame)
                    except Exception as exc:  # robustness: never die on one frame
                        logger.warning("Frame processing error (skipped): %s", exc)

                    if not headless and self.config.ui.show_dashboard:
                        cv2.imshow(_WINDOW, frame)
                    if not headless:
                        if not self._handle_keys(cv2):
                            break

                    processed += 1
                    if max_frames is not None and processed >= max_frames:
                        break
        finally:
            self._running = False
        return processed

    def _process_frame(self, tracker: HandTracker, frame):
        gesture = Gesture.NONE
        confidence = 0.0
        dispatch = None

        hands = [] if self._paused else tracker.process(frame)
        if hands:
            hand = hands[0]
            result = self.classifier.classify(hand)
            gesture, confidence = result.gesture, result.confidence
            dispatch = self.dispatcher.dispatch(result)
            self.dashboard.record_gesture(gesture)
            if self.config.ui.show_skeleton:
                self.dashboard.draw_skeleton(frame, hand)
        else:
            if self.dispatcher.mouse.is_dragging:
                self.dispatcher.mouse.end_drag()

        state = DashboardState(
            metrics=self.monitor.snapshot(),
            gesture=gesture,
            action=(
                dispatch.action
                if dispatch
                else ("PAUSED" if self._paused else "")
            ),
            confidence=confidence,
            volume=dispatch.volume if dispatch else None,
            brightness=dispatch.brightness if dispatch else None,
        )
        return self.dashboard.render(frame, state)

    # --- input handling ---------------------------------------------------

    def _handle_keys(self, cv2) -> bool:
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):  # q or ESC
            return False
        if key == ord("p"):
            self._paused = not self._paused
            logger.info("Paused" if self._paused else "Resumed")
        elif key == ord("s"):
            self._open_settings(cv2)
        elif key in (ord("1"), ord("2"), ord("3")):
            self._switch_profile(
                {ord("1"): "General", ord("2"): "Gamer", ord("3"): "Designer"}[key]
            )
        return True

    def _switch_profile(self, name: str) -> None:
        try:
            self.config = ConfigManager().load(name)
            self.dispatcher.reconfigure(self.config)
            self.classifier.set_backend(
                RuleBasedBackend(self.config.thresholds.to_thresholds())
            )
            if self.dry_run:
                self._disarm_controllers()
            self.dashboard.set_theme(self.config.ui.theme)
            logger.info("Switched to profile '%s'", name)
        except VisionOSError as exc:
            logger.error("Could not switch profile: %s", exc)

    def _open_settings(self, cv2) -> None:
        """Open the Tkinter settings editor on the MAIN thread.

        Tkinter is not thread-safe (and on macOS must run on the main thread),
        so the capture loop is paused while the modal editor is open instead of
        spawning a worker thread, which previously caused freezes/crashes.
        """
        from visionos.ui.settings_window import SettingsWindow

        logger.info("Opening settings (capture paused) ...")
        try:
            cv2.destroyWindow(_WINDOW)
        except Exception:  # pragma: no cover - window may not exist yet
            pass
        try:
            SettingsWindow(self.config, on_save=self._on_settings_saved).run()
        except Exception as exc:  # pragma: no cover - GUI/runtime guard
            logger.error("Settings window error: %s", exc)
        logger.info("Settings closed; resuming capture")

    def _on_settings_saved(self, config: AppConfig) -> None:
        self.config = config
        self.dispatcher.reconfigure(config)
        if self.dry_run:
            self._disarm_controllers()
        self.dashboard.set_theme(config.ui.theme)
        logger.info("Applied edited settings live")
