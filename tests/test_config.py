"""Tests for typed configuration: dataclass round-trips and disk persistence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from visionos.config.settings import (
    AppConfig,
    ConfigManager,
    SmoothingSettings,
    ThresholdSettings,
)
from visionos.core.smoothing import OneEuroConfig
from visionos.gestures.rules import GestureThresholds
from visionos.utils.exceptions import ConfigError


def test_appconfig_dict_round_trip_preserves_values() -> None:
    original = AppConfig(profile_name="Custom")
    original.camera.width = 640
    original.smoothing.beta = 0.05
    original.ui.theme = "neon"
    original.action_map = {"scroll": "scroll"}

    restored = AppConfig.from_dict(original.to_dict())

    assert restored.profile_name == "Custom"
    assert restored.camera.width == 640
    assert restored.smoothing.beta == 0.05
    assert restored.ui.theme == "neon"
    assert restored.action_map == {"scroll": "scroll"}


def test_from_dict_fills_defaults_for_missing_sections() -> None:
    restored = AppConfig.from_dict({"profile_name": "Sparse"})
    assert restored.profile_name == "Sparse"
    # Missing sections fall back to dataclass defaults.
    assert restored.camera.index == 0
    assert restored.ui.show_dashboard is True


def test_from_dict_rejects_unknown_keys() -> None:
    with pytest.raises(ConfigError):
        AppConfig.from_dict({"camera": {"not_a_real_field": 1}})


def test_smoothing_settings_maps_to_one_euro() -> None:
    s = SmoothingSettings(min_cutoff=2.0, beta=0.01, d_cutoff=1.5)
    euro = s.to_one_euro()
    assert isinstance(euro, OneEuroConfig)
    assert (euro.min_cutoff, euro.beta, euro.d_cutoff) == (2.0, 0.01, 1.5)


def test_threshold_settings_maps_to_thresholds() -> None:
    t = ThresholdSettings(pinch=0.3, spread=0.8, fist_curl=0.5)
    thr = t.to_thresholds()
    assert isinstance(thr, GestureThresholds)
    assert (thr.pinch, thr.spread, thr.fist_curl) == (0.3, 0.8, 0.5)


def test_config_manager_save_and_load(tmp_path: Path) -> None:
    manager = ConfigManager(profile_dir=tmp_path)
    cfg = AppConfig(profile_name="Studio")
    cfg.controls.scroll_speed = 200

    path = manager.save(cfg)
    assert path.exists()
    # File is named after the lower-cased profile name.
    assert path.name == "studio.json"

    loaded = manager.load("Studio")
    assert loaded.profile_name == "Studio"
    assert loaded.controls.scroll_speed == 200


def test_config_manager_lists_available_profiles(tmp_path: Path) -> None:
    manager = ConfigManager(profile_dir=tmp_path)
    manager.save(AppConfig(profile_name="Alpha"))
    manager.save(AppConfig(profile_name="Beta"))
    assert manager.available_profiles() == ["alpha", "beta"]


def test_config_manager_unknown_profile_returns_defaults(tmp_path: Path) -> None:
    manager = ConfigManager(profile_dir=tmp_path)
    cfg = manager.load("does_not_exist")
    # Falls back to defaults with a capitalised profile name rather than raising.
    assert cfg.profile_name == "Does_not_exist"


def test_config_manager_corrupt_file_raises(tmp_path: Path) -> None:
    manager = ConfigManager(profile_dir=tmp_path)
    (tmp_path / "broken.json").write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ConfigError):
        manager.load("broken")


def test_shipped_profiles_are_valid_json_and_loadable() -> None:
    """The three profiles committed to the repo must parse into AppConfig."""
    repo_profiles = Path("config/profiles")
    if not repo_profiles.exists():  # pragma: no cover - layout guard
        pytest.skip("profile directory not present in this checkout")
    for name in ("general", "gamer", "designer"):
        data = json.loads((repo_profiles / f"{name}.json").read_text("utf-8"))
        cfg = AppConfig.from_dict(data)
        assert cfg.profile_name
