"""Command-line interface for VisionOS Gesture Control.

Living inside the package means the same entry point backs three launch styles:
``python main.py`` (repo checkout), ``python -m visionos`` (installed module)
and the ``visionos`` console script declared in ``pyproject.toml``.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Iterator, Optional

from visionos.app import VisionOSApp
from visionos.config.settings import ConfigManager
from visionos.utils.exceptions import VisionOSError
from visionos.utils.logger import configure_logging, get_logger


def parse_args(argv: Optional[list] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="visionos",
        description="Real-time touchless computer control via hand gestures.",
    )
    parser.add_argument("--profile", default="General", help="User profile to load")
    parser.add_argument(
        "--camera", type=int, default=None, help="Override camera index"
    )
    parser.add_argument(
        "--list-profiles", action="store_true", help="List profiles and exit"
    )
    parser.add_argument(
        "--no-dashboard", action="store_true", help="Hide the HUD overlay"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run normally but do NOT actuate the mouse/keyboard (safe preview)",
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Watch the pipeline on your webcam without controlling the OS "
        "(implies --dry-run)",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="Verify the install and pipeline headlessly (no camera) and exit",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--log-file", type=Path, default=None, help="Optional log file path"
    )
    return parser.parse_args(argv)


def _synthetic_frames(n: int) -> Iterator["object"]:
    """Generate placeholder frames to exercise the pipeline without a camera."""
    import numpy as np

    rng = np.random.default_rng(0)
    for i in range(n):
        frame = (rng.integers(0, 40, (480, 640, 3))).astype("uint8")
        # a moving bright blob so the dashboard shows motion
        cx = 80 + (i * 13) % 480
        frame[200:280, cx : cx + 80] = 200
        yield frame


def _run_selftest(args: argparse.Namespace, log) -> int:
    """Exercise every pipeline stage on synthetic frames; report and exit."""
    log.info("Running self-test (no camera required) ...")
    checks = []

    def record(label: str, ok: bool, detail: str = "") -> None:
        checks.append((label, ok, detail))

    try:
        import cv2  # noqa: F401

        record("OpenCV import", True, "cv2 available")
    except Exception as exc:
        record("OpenCV import", False, str(exc))

    try:
        import mediapipe  # noqa: F401

        record("MediaPipe import", True, f"v{mediapipe.__version__}")
    except Exception as exc:
        record("MediaPipe import", False, str(exc))

    frames_done = 0
    try:
        cfg = ConfigManager().load(args.profile)
        app = VisionOSApp(cfg, dry_run=True)
        frames_done = app.run_frames(
            _synthetic_frames(30), headless=True, max_frames=30
        )
        record(
            "End-to-end pipeline",
            frames_done == 30,
            f"{frames_done}/30 frames processed",
        )
    except Exception as exc:
        record("End-to-end pipeline", False, repr(exc))

    print("\n  VisionOS self-test")
    print("  " + "-" * 46)
    all_ok = True
    for label, ok, detail in checks:
        mark = "PASS" if ok else "FAIL"
        all_ok = all_ok and ok
        print(f"  [{mark}] {label:<22} {detail}")
    print("  " + "-" * 46)
    if all_ok:
        print("  All checks passed. Run `python main.py` to start.\n")
        return 0
    print(
        "  Some checks failed. If MediaPipe failed, try:\n"
        '      pip install "mediapipe<0.10.15"\n'
    )
    return 1


def main(argv: Optional[list] = None) -> int:
    args = parse_args(argv)
    configure_logging(
        level=logging.DEBUG if args.debug else logging.INFO,
        log_file=args.log_file,
    )
    log = get_logger("cli")

    manager = ConfigManager()
    if args.list_profiles:
        for name in manager.available_profiles():
            print(name)
        return 0

    if args.selftest:
        return _run_selftest(args, log)

    config = manager.load(args.profile)
    if args.camera is not None:
        config.camera.index = args.camera
    if args.no_dashboard:
        config.ui.show_dashboard = False

    dry_run = args.dry_run or args.simulate
    if args.simulate:
        log.info("Simulate mode: webcam preview only, OS control disabled")

    try:
        VisionOSApp(config, dry_run=dry_run).run()
    except VisionOSError as exc:
        log.error("Fatal: %s", exc)
        return 1
    except KeyboardInterrupt:
        log.info("Interrupted by user")
    return 0
