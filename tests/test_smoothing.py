"""Tests for the One Euro Filter and the :class:`PointSmoother` wrapper.

These verify the *behavioural* contract the cursor pipeline relies on, rather
than exact filter coefficients: noise is attenuated when the signal is steady,
fast motion is tracked with low lag, and ``reset`` returns the filter to a
pristine state.
"""

from __future__ import annotations

from visionos.core.smoothing import (
    OneEuroConfig,
    OneEuroFilter,
    PointSmoother,
)


def test_first_sample_is_passed_through() -> None:
    """The filter cannot smooth without history, so it echoes the first value."""
    f = OneEuroFilter()
    assert f(5.0, 0.0) == 5.0


def test_steady_noise_is_attenuated() -> None:
    """A noisy signal around a constant mean should be pulled toward the mean."""
    f = OneEuroFilter(OneEuroConfig(min_cutoff=0.5, beta=0.0))
    noisy = [10.0, 10.6, 9.4, 10.5, 9.5, 10.4, 9.6]
    out = [f(v, i / 30.0) for i, v in enumerate(noisy)]
    # The final filtered value sits much closer to the mean (10) than the raw
    # sample's deviation would suggest.
    assert abs(out[-1] - 10.0) < abs(noisy[-1] - 10.0)


def test_fast_motion_tracks_with_low_lag() -> None:
    """With speed coefficient engaged, a ramp should be followed closely."""
    f = OneEuroFilter(OneEuroConfig(min_cutoff=1.0, beta=1.0))
    last = 0.0
    for i in range(1, 40):
        last = f(float(i), i / 30.0)
    # After tracking a steady ramp the output should be within a couple of
    # units of the true position (i.e. not lagging far behind).
    assert abs(last - 39.0) < 3.0


def test_reset_clears_history() -> None:
    f = OneEuroFilter()
    f(100.0, 0.0)
    f(200.0, 1 / 30.0)
    f.reset()
    # After reset the next sample is again passed straight through.
    assert f(7.0, 0.0) == 7.0


def test_point_smoother_smooths_both_axes() -> None:
    smoother = PointSmoother(OneEuroConfig(min_cutoff=0.5, beta=0.0))
    smoother.smooth(0.0, 0.0, 0.0)
    x, y = smoother.smooth(1.0, 1.0, 1 / 30.0)
    # A single step toward (1, 1) should not jump the whole way when smoothed.
    assert 0.0 < x < 1.0
    assert 0.0 < y < 1.0


def test_point_smoother_update_config_is_live() -> None:
    smoother = PointSmoother()
    new = OneEuroConfig(min_cutoff=2.5, beta=0.02, d_cutoff=1.0)
    smoother.update_config(new)
    # The replacement config propagates to both underlying axis filters.
    assert smoother._fx.config is new  # type: ignore[attr-defined]
    assert smoother._fy.config is new  # type: ignore[attr-defined]


def test_point_smoother_reset_restarts_passthrough() -> None:
    smoother = PointSmoother(OneEuroConfig(min_cutoff=0.5, beta=0.0))
    smoother.smooth(5.0, 5.0, 0.0)
    smoother.smooth(6.0, 6.0, 1 / 30.0)
    smoother.reset()
    x, y = smoother.smooth(9.0, 3.0, 0.0)
    assert (x, y) == (9.0, 3.0)
