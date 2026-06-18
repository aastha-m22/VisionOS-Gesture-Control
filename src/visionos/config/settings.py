"""Typed application configuration with JSON-backed user profiles.

Configuration is modelled as a tree of frozen-ish dataclasses so every setting
is discoverable, type-checked and documented in one place, instead of being
scattered through ``cfg["some"]["magic"]["string"]`` dictionary lookups. The
:class:`ConfigManager` handles (de)serialisation to the ``config/profiles``
directory and exposes the three shipped profiles: General, Gamer and Designer.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, List

from visionos.core.smoothing import OneEuroConfig
from visionos.gestures.rules import GestureThresholds
from visionos.utils.exceptions import ConfigError
from visionos.utils.logger import get_logger

logger = get_logger("config.settings")

DEFAULT_PROFILE_DIR = Path("config/profiles")


@dataclass
class CameraSettings:
    index: int = 0
    width: int = 1280
    height: int = 720
    flip_horizontal: bool = True  # mirror so movement feels natural


@dataclass
class TrackingSettings:
    max_hands: int = 1
    detection_confidence: float = 0.7
    tracking_confidence: float = 0.6
    model_complexity: int = 1


@dataclass
class SmoothingSettings:
    """Maps directly onto :class:`OneEuroConfig` plus a sensitivity multiplier."""

    min_cutoff: float = 1.0
    beta: float = 0.007
    d_cutoff: float = 1.0
    sensitivity: float = 1.6  # gain applied when mapping camera → screen

    def to_one_euro(self) -> OneEuroConfig:
        return OneEuroConfig(self.min_cutoff, self.beta, self.d_cutoff)


@dataclass
class ThresholdSettings:
    pinch: float = 0.35
    spread: float = 0.9
    fist_curl: float = 0.55

    def to_thresholds(self) -> GestureThresholds:
        return GestureThresholds(self.pinch, self.spread, self.fist_curl)


@dataclass
class ControlSettings:
    scroll_speed: int = 120
    volume_step: float = 2.0
    brightness_step: float = 2.0
    screenshot_dir: str = "screenshots"
    cursor_margin: float = 0.12  # dead-band at frame edges for full-screen reach


@dataclass
class UISettings:
    theme: str = "dark"
    show_dashboard: bool = True
    show_skeleton: bool = True
    history_length: int = 8


@dataclass
class AppConfig:
    """Root configuration object for one user profile."""

    profile_name: str = "General"
    camera: CameraSettings = field(default_factory=CameraSettings)
    tracking: TrackingSettings = field(default_factory=TrackingSettings)
    smoothing: SmoothingSettings = field(default_factory=SmoothingSettings)
    thresholds: ThresholdSettings = field(default_factory=ThresholdSettings)
    controls: ControlSettings = field(default_factory=ControlSettings)
    ui: UISettings = field(default_factory=UISettings)
    # Gesture → action-name mapping; lets profiles remap behaviour without code.
    action_map: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        try:
            return cls(
                profile_name=data.get("profile_name", "General"),
                camera=CameraSettings(**data.get("camera", {})),
                tracking=TrackingSettings(**data.get("tracking", {})),
                smoothing=SmoothingSettings(**data.get("smoothing", {})),
                thresholds=ThresholdSettings(**data.get("thresholds", {})),
                controls=ControlSettings(**data.get("controls", {})),
                ui=UISettings(**data.get("ui", {})),
                action_map=data.get("action_map", {}),
            )
        except TypeError as exc:  # unknown / mistyped key
            raise ConfigError(f"Invalid configuration schema: {exc}") from exc


class ConfigManager:
    """Loads, lists and persists user profiles in a JSON directory."""

    def __init__(self, profile_dir: Path = DEFAULT_PROFILE_DIR) -> None:
        self.profile_dir = Path(profile_dir)
        self.profile_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, name: str) -> Path:
        return self.profile_dir / f"{name.lower()}.json"

    def available_profiles(self) -> List[str]:
        return sorted(p.stem for p in self.profile_dir.glob("*.json"))

    def load(self, name: str) -> AppConfig:
        path = self._path_for(name)
        if not path.exists():
            logger.warning("Profile '%s' not found; using built-in defaults", name)
            return replace(AppConfig(), profile_name=name.capitalize())
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigError(f"Could not read profile '{name}': {exc}") from exc
        logger.info("Loaded profile '%s'", name)
        return AppConfig.from_dict(data)

    def save(self, config: AppConfig) -> Path:
        path = self._path_for(config.profile_name)
        try:
            path.write_text(
                json.dumps(config.to_dict(), indent=2, sort_keys=False),
                encoding="utf-8",
            )
        except OSError as exc:
            raise ConfigError(f"Could not save profile: {exc}") from exc
        logger.info("Saved profile '%s' → %s", config.profile_name, path)
        return path
