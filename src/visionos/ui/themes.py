"""Colour themes for the on-screen dashboard.

Colours are stored as BGR tuples because that is what OpenCV expects, avoiding
per-draw conversions. Each :class:`Theme` is a flat, immutable palette so the
dashboard renderer never hard-codes a colour.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

BGR = Tuple[int, int, int]


@dataclass(frozen=True)
class Theme:
    name: str
    background: BGR
    panel: BGR
    text: BGR
    text_dim: BGR
    accent: BGR
    good: BGR
    warn: BGR
    bad: BGR
    skeleton: BGR


_THEMES: Dict[str, Theme] = {
    "dark": Theme(
        name="dark",
        background=(24, 24, 28),
        panel=(40, 40, 48),
        text=(240, 240, 240),
        text_dim=(160, 160, 170),
        accent=(255, 180, 60),
        good=(90, 220, 120),
        warn=(70, 200, 240),
        bad=(80, 80, 240),
        skeleton=(255, 200, 90),
    ),
    "light": Theme(
        name="light",
        background=(235, 235, 240),
        panel=(255, 255, 255),
        text=(30, 30, 30),
        text_dim=(110, 110, 110),
        accent=(200, 120, 20),
        good=(60, 170, 90),
        warn=(40, 150, 210),
        bad=(60, 60, 210),
        skeleton=(210, 140, 40),
    ),
    "neon": Theme(
        name="neon",
        background=(18, 12, 24),
        panel=(40, 20, 50),
        text=(230, 255, 255),
        text_dim=(150, 120, 170),
        accent=(255, 60, 200),
        good=(120, 255, 180),
        warn=(60, 220, 255),
        bad=(80, 80, 255),
        skeleton=(255, 80, 220),
    ),
}


def get_theme(name: str) -> Theme:
    """Return a theme by name, defaulting to dark if unknown."""
    return _THEMES.get(name, _THEMES["dark"])


def theme_names() -> list[str]:
    return list(_THEMES.keys())
