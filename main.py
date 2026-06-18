"""VisionOS Gesture Control — command-line entry point.

Usage::

    python main.py                      # run with the General profile
    python main.py --profile Gamer      # run a specific profile
    python main.py --list-profiles      # show available profiles
    python main.py --camera 1 --debug   # override camera and enable debug logs

This is a thin wrapper that works from a bare checkout (no installation needed);
the real logic lives in :mod:`visionos.cli`.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running directly from a checkout without installation.
sys.path.insert(0, str(Path(__file__).parent / "src"))

from visionos.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
