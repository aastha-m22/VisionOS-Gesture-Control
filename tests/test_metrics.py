"""Tests for the :class:`PerformanceMonitor` FPS and snapshot logic."""

from __future__ import annotations

import time

from visionos.utils.metrics import MetricsSnapshot, PerformanceMonitor


def test_fps_is_zero_before_two_frames() -> None:
    monitor = PerformanceMonitor()
    assert monitor.fps == 0.0
    monitor.tick()
    # A single frame is still insufficient to define a rate.
    assert monitor.fps == 0.0


def test_fps_reflects_frame_cadence() -> None:
    monitor = PerformanceMonitor(window=30)
    # Feed ~10 ms spacing → roughly 100 FPS; allow a wide tolerance because the
    # test sleeps on a real clock.
    for _ in range(10):
        monitor.tick()
        time.sleep(0.01)
    assert monitor.fps > 30.0


def test_window_bounds_the_timestamp_buffer() -> None:
    monitor = PerformanceMonitor(window=5)
    for _ in range(20):
        monitor.tick()
    # The deque is capped at the configured window size.
    assert len(monitor._timestamps) == 5  # type: ignore[attr-defined]


def test_snapshot_returns_dataclass() -> None:
    monitor = PerformanceMonitor()
    monitor.tick()
    time.sleep(0.005)
    monitor.tick()
    snap = monitor.snapshot()
    assert isinstance(snap, MetricsSnapshot)
    assert snap.fps >= 0.0
    # cpu/memory are either floats (psutil present) or None (graceful degrade).
    assert snap.cpu_percent is None or isinstance(snap.cpu_percent, float)
    assert snap.memory_mb is None or isinstance(snap.memory_mb, float)
