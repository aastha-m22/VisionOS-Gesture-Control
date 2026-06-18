"""Enables ``python -m visionos`` as a launch entry point."""

from __future__ import annotations

from visionos.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
