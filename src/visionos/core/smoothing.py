"""Adaptive smoothing using the One Euro Filter (Casiez et al., 2012).

The One Euro Filter is the canonical solution to the precision/responsiveness
trade-off in pointer control: at low speeds it applies a low cutoff frequency
(heavy smoothing → high precision, eliminating jitter), while at high speeds it
raises the cutoff (light smoothing → low latency, eliminating lag). This is
exactly the "slow = precise, fast = responsive" behaviour required for a usable
gesture cursor, and it is far superior to a fixed exponential moving average.

Reference: Géry Casiez, Nicolas Roussel, Daniel Vogel,
"1€ Filter: A Simple Speed-based Low-pass Filter for Noisy Input in
Interactive Systems", CHI 2012.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple


def _smoothing_alpha(cutoff: float, dt: float) -> float:
    """Compute the EMA factor for a given cutoff frequency and time delta."""
    tau = 1.0 / (2.0 * math.pi * cutoff)
    return 1.0 / (1.0 + tau / dt)


class _LowPassFilter:
    """A first-order exponential low-pass filter with externally set alpha."""

    def __init__(self) -> None:
        self._value: Optional[float] = None

    @property
    def initialised(self) -> bool:
        return self._value is not None

    @property
    def last(self) -> float:
        return self._value if self._value is not None else 0.0

    def filter(self, value: float, alpha: float) -> float:
        if self._value is None:
            self._value = value
        else:
            self._value = alpha * value + (1.0 - alpha) * self._value
        return self._value


@dataclass
class OneEuroConfig:
    """Tunable parameters for :class:`OneEuroFilter`.

    Args:
        min_cutoff: Baseline cutoff frequency (Hz). Lower → smoother but laggier
            when the hand is nearly still.
        beta: Speed coefficient. Higher → less lag during fast motion.
        d_cutoff: Cutoff for the derivative (speed estimate) low-pass.
    """

    min_cutoff: float = 1.0
    beta: float = 0.007
    d_cutoff: float = 1.0


class OneEuroFilter:
    """One-dimensional One Euro Filter."""

    def __init__(self, config: Optional[OneEuroConfig] = None) -> None:
        self.config = config or OneEuroConfig()
        self._x = _LowPassFilter()
        self._dx = _LowPassFilter()
        self._last_time: Optional[float] = None

    def reset(self) -> None:
        self._x = _LowPassFilter()
        self._dx = _LowPassFilter()
        self._last_time = None

    def __call__(self, value: float, timestamp: float) -> float:
        if self._last_time is not None and timestamp > self._last_time:
            dt = timestamp - self._last_time
        else:
            dt = 1.0 / 30.0  # assume 30 FPS on the first sample
        self._last_time = timestamp

        prev = self._x.last if self._x.initialised else value
        dx = (value - prev) / dt
        edx = self._dx.filter(dx, _smoothing_alpha(self.config.d_cutoff, dt))

        cutoff = self.config.min_cutoff + self.config.beta * abs(edx)
        return self._x.filter(value, _smoothing_alpha(cutoff, dt))


class PointSmoother:
    """Convenience wrapper smoothing an (x, y) point with two One Euro filters."""

    def __init__(self, config: Optional[OneEuroConfig] = None) -> None:
        self._fx = OneEuroFilter(config)
        self._fy = OneEuroFilter(config)
        self._config = config or OneEuroConfig()

    def update_config(self, config: OneEuroConfig) -> None:
        """Live-update the filter parameters (used by the settings UI)."""
        self._config = config
        self._fx.config = config
        self._fy.config = config

    def reset(self) -> None:
        self._fx.reset()
        self._fy.reset()

    def smooth(self, x: float, y: float, timestamp: float) -> Tuple[float, float]:
        return self._fx(x, timestamp), self._fy(y, timestamp)
