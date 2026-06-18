"""Central logging configuration.

A single :func:`get_logger` factory is used across the codebase so that every
module shares one consistent, colourised, optionally file-backed logger. This
avoids the common anti-pattern of each module calling ``logging.basicConfig``.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

_CONFIGURED = False

_LEVEL_COLOURS = {
    logging.DEBUG: "\033[37m",     # grey
    logging.INFO: "\033[36m",      # cyan
    logging.WARNING: "\033[33m",   # yellow
    logging.ERROR: "\033[31m",     # red
    logging.CRITICAL: "\033[41m",  # red background
}
_RESET = "\033[0m"


class _ColourFormatter(logging.Formatter):
    """Formatter that prefixes the level name with an ANSI colour."""

    def __init__(self, use_colour: bool = True) -> None:
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        )
        self.use_colour = use_colour and sys.stderr.isatty()

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        if self.use_colour:
            colour = _LEVEL_COLOURS.get(record.levelno, "")
            return f"{colour}{message}{_RESET}"
        return message


def configure_logging(
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
) -> None:
    """Configure the root logger exactly once.

    Args:
        level: Minimum level emitted to the console.
        log_file: Optional path; when given, all records (DEBUG and up) are also
            written there without colour codes.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    root = logging.getLogger("visionos")
    root.setLevel(logging.DEBUG)
    root.propagate = False

    console = logging.StreamHandler(sys.stderr)
    console.setLevel(level)
    console.setFormatter(_ColourFormatter(use_colour=True))
    root.addHandler(console)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(_ColourFormatter(use_colour=False))
        root.addHandler(file_handler)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced child logger (e.g. ``visionos.core.hand_tracker``)."""
    if not _CONFIGURED:
        configure_logging()
    return logging.getLogger(f"visionos.{name}")
