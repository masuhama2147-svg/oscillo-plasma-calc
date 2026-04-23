"""Analytic sanity checks for electrical calculations."""
import math
import numpy as np
import pytest

from oscillo_plasma_calc.electrical import (
    instantaneous_power, absorbed_energy, mean_power, v_rms,
)
from oscillo_plasma_calc.signal.peaks import detect_vpp, detect_ipp


def _sin_pair(V0=1.0, I0=1.0, phi=0.0, f=1.0, n=10_000):
    T = 1.0 / f
    t = np.linspace(0, T, n, endpoint=False)
    v = V0 * np.sin(2 * np.pi * f * t)
    i = I0 * np.sin(2 * np.pi * f * t - phi)
    return t, v, i


def test_instant_power_shape():
    t, v, i = _sin_pair()
    p = instantaneous_power(v, i)
    assert p.value.shape == v.shape


def test_mean_power_in_phase():
    # P̄ = ½ V0 I0 cos(φ) for sin pair
    V0, I0, phi = 100.0, 2.5, 0.0
    t, v, i = _sin_pair(V0, I0, phi)
    res = mean_power(t, v, i)
    expected = 0.5 * V0 * I0 * math.cos(phi)
    assert res.value == pytest.approx(expected, rel=1e-3)


def test_mean_power_quadrature_zero():
    # V·I sinusoids in quadrature → mean power = 0. Discretization error is
    # bounded by ~V0 I0 / N for trapezoidal integration over non-integer periods.
    V0, I0, N = 100.0, 2.5, 10_000
    t, v, i = _sin_pair(V0, I0, phi=math.pi / 2, n=N)
    res = mean_power(t, v, i)
    assert abs(res.value) < V0 * I0 / N


def test_rms_half_sqrt2():
    V0 = 10.0
    t, v, _ = _sin_pair(V0, 1.0, 0.0)
    res = v_rms(t, v)
    assert res.value == pytest.approx(V0 / math.sqrt(2), rel=1e-3)


def test_vpp_ipp():
    t, v, i = _sin_pair(V0=3.0, I0=1.5)
    assert detect_vpp(v).value == pytest.approx(6.0, rel=1e-6)
    assert detect_ipp(i).value == pytest.approx(3.0, rel=1e-6)


def test_energy_consistency():
    t, v, i = _sin_pair(100, 2.5, phi=0.3)
    e = absorbed_energy(t, v, i)
    p = mean_power(t, v, i)
    T = t[-1] - t[0]
    assert e.value == pytest.approx(p.value * T, rel=1e-3)
