"""Runtime performance metrics: frame rate, CPU and memory usage.

``psutil`` is used for system metrics but is treated as optional so the core
pipeline still runs in minimal environments; when it is unavailable the CPU and
memory readings gracefully degrade to ``None``.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Optional

from visionos.utils.logger import get_logger

logger = get_logger("utils.metrics")

try:
    import psutil

    _PROCESS = psutil.Process()
    _HAS_PSUTIL = True
except Exception:  # pragma: no cover - environment dependent
    psutil = None  # type: ignore[assignment]
    _PROCESS = None
    _HAS_PSUTIL = False
    logger.warning("psutil not available; CPU/memory metrics disabled")


@dataclass(frozen=True)
class MetricsSnapshot:
    """Immutable view of the metrics at a single instant."""

    fps: float
    cpu_percent: Optional[float]
    memory_mb: Optional[float]


class PerformanceMonitor:
    """Tracks a rolling FPS average and samples process resource usage.

    FPS is computed from a sliding window of frame timestamps to smooth out
    per-frame jitter. CPU and memory are sampled at a throttled interval because
    ``psutil`` calls are comparatively expensive.
    """

    def __init__(self, window: int = 30, sample_interval: float = 0.5) -> None:
        self._timestamps: Deque[float] = deque(maxlen=window)
        self._sample_interval = sample_interval
        self._last_sample = 0.0
        self._cpu: Optional[float] = None
        self._mem: Optional[float] = None
        if _HAS_PSUTIL:
            _PROCESS.cpu_percent(None)  # prime the counter

    def tick(self) -> None:
        """Record that a frame was processed."""
        self._timestamps.append(time.perf_counter())

    @property
    def fps(self) -> float:
        if len(self._timestamps) < 2:
            return 0.0
        span = self._timestamps[-1] - self._timestamps[0]
        if span <= 0:
            return 0.0
        return (len(self._timestamps) - 1) / span

    def _maybe_sample_system(self) -> None:
        now = time.perf_counter()
        if not _HAS_PSUTIL or now - self._last_sample < self._sample_interval:
            return
        self._last_sample = now
        try:
            self._cpu = _PROCESS.cpu_percent(None)
            self._mem = _PROCESS.memory_info().rss / (1024 * 1024)
        except Exception as exc:  # pragma: no cover - environment dependent
            logger.debug("Failed to sample system metrics: %s", exc)

    def snapshot(self) -> MetricsSnapshot:
        """Return the current metrics, sampling the system if due."""
        self._maybe_sample_system()
        return MetricsSnapshot(fps=self.fps, cpu_percent=self._cpu, memory_mb=self._mem)
