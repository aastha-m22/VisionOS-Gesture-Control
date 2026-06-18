"""Cross-platform system volume control.

Three backends are detected at runtime and hidden behind one interface:

* Windows  → ``pycaw`` (Core Audio API)
* macOS    → ``osascript`` (``set volume output volume ...``)
* Linux    → ``pactl`` / ``amixer``

If none is usable the controller disables itself and the rest of the app keeps
working — the visual volume indicator still renders, it simply has no OS effect.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
from typing import Optional

from visionos.controllers.base import BaseController


class _VolumeBackend:
    def set_volume(self, percent: float) -> None:  # pragma: no cover - abstract
        raise NotImplementedError

    def get_volume(self) -> Optional[float]:  # pragma: no cover - abstract
        return None


class _WindowsVolume(_VolumeBackend):
    def __init__(self) -> None:
        from ctypes import POINTER, cast

        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        self._volume = cast(interface, POINTER(IAudioEndpointVolume))

    def set_volume(self, percent: float) -> None:
        self._volume.SetMasterVolumeLevelScalar(max(0.0, min(percent, 100.0)) / 100.0, None)

    def get_volume(self) -> Optional[float]:
        return self._volume.GetMasterVolumeLevelScalar() * 100.0


class _MacVolume(_VolumeBackend):
    def set_volume(self, percent: float) -> None:
        level = int(max(0.0, min(percent, 100.0)))
        subprocess.run(
            ["osascript", "-e", f"set volume output volume {level}"],
            check=False,
        )


class _LinuxVolume(_VolumeBackend):
    def __init__(self) -> None:
        self._tool = "pactl" if shutil.which("pactl") else "amixer"

    def set_volume(self, percent: float) -> None:
        level = int(max(0.0, min(percent, 100.0)))
        if self._tool == "pactl":
            subprocess.run(
                ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{level}%"],
                check=False,
            )
        else:
            subprocess.run(
                ["amixer", "set", "Master", f"{level}%"], check=False
            )


def _make_backend() -> Optional[_VolumeBackend]:
    system = platform.system()
    try:
        if system == "Windows":
            return _WindowsVolume()
        if system == "Darwin":
            return _MacVolume()
        if system == "Linux" and (shutil.which("pactl") or shutil.which("amixer")):
            return _LinuxVolume()
    except Exception:  # pragma: no cover - backend init failure
        return None
    return None


class VolumeController(BaseController):
    """Sets the system master volume from a 0–100 percentage."""

    name = "volume"

    def __init__(self) -> None:
        super().__init__()
        self._backend = _make_backend()
        self._current = 50.0
        if self._backend is None:
            self._disable("no supported audio backend found")
        else:
            level = self._backend.get_volume()
            if level is not None:
                self._current = level

    @property
    def current(self) -> float:
        return self._current

    def set_volume(self, percent: float) -> None:
        percent = max(0.0, min(percent, 100.0))
        self._current = percent
        if self.available and self._backend is not None:
            try:
                self._backend.set_volume(percent)
            except Exception as exc:  # pragma: no cover
                self._disable(f"runtime error: {exc}")
