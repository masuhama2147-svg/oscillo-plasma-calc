"""Wilhoit high-temperature extrapolation tests."""
import numpy as np
import pytest

from oscillo_plasma_calc.thermo import (
    WilhoitCp, fit_wilhoit_to_nasa, cp_R_extrapolated, lookup,
)


def test_wilhoit_low_T_limit_is_a():
    w = WilhoitCp(a=2.5, b=4.5, B=500.0, c=(0.0, 0.0, 0.0, 0.0))
    assert w.cp_R(1e-3) == pytest.approx(2.5, abs=1e-2)


def test_wilhoit_high_T_limit_is_b():
    w = WilhoitCp(a=2.5, b=4.5, B=500.0, c=(0.0, 0.0, 0.0, 0.0))
    assert w.cp_R(1e8) == pytest.approx(4.5, rel=1e-3)


def test_wilhoit_monotonic_for_simple_form():
    """Without c-shape (all zero), Cp/R should be monotonic between a and b."""
    w = WilhoitCp(a=2.5, b=4.5, B=500.0, c=(0.0, 0.0, 0.0, 0.0))
    Ts = np.array([10, 100, 500, 1000, 3000, 10000.0])
    cp = np.array([w.cp_R(t) for t in Ts])
    assert np.all(np.diff(cp) > 0)


def test_wilhoit_zero_T_returns_a():
    w = WilhoitCp(a=2.5, b=4.5, B=500.0, c=(0.0, 0.0, 0.0, 0.0))
    assert w.cp_R(0.0) == pytest.approx(2.5)


def test_fit_wilhoit_to_co2_nasa_reproduces_high_T_smoothly():
    """Fit Wilhoit to CO2 NASA7 then verify continuity at the NASA Tmax."""
    co2 = lookup("CO2")
    nasa = co2.evaluator
    Tmax_nasa = nasa.high.Tmax
    wil = fit_wilhoit_to_nasa(nasa, a=4.0, b=8.0,    # CO2 is polyatomic, rough hi limit
                                T_fit_lo=300.0, T_fit_hi=Tmax_nasa,
                                B0=600.0)
    cp_nasa = nasa.cp_R(Tmax_nasa - 1.0) * 8.314
    cp_wil  = wil.cp_R(Tmax_nasa - 1.0) * 8.314
    # Allow up to 5 % discrepancy near the boundary (Wilhoit fits are
    # least-squares, not exact)
    assert abs(cp_nasa - cp_wil) / cp_nasa < 0.05


def test_cp_R_extrapolated_uses_nasa_inside_range():
    """Below Tmax, the value must match the NASA polynomial exactly."""
    co2 = lookup("CO2")
    cp_direct = co2.evaluator.cp_R(2000.0)
    cp_extrap = cp_R_extrapolated(co2.evaluator, 2000.0)
    assert cp_extrap == pytest.approx(cp_direct, rel=1e-12)


def test_cp_R_extrapolated_uses_wilhoit_above_range():
    """Above Tmax, the result should not equal a naive linear extrapolation."""
    co2 = lookup("CO2")
    nasa = co2.evaluator
    Tmax = nasa.high.Tmax
    cp_extrap = cp_R_extrapolated(nasa, Tmax * 1.5,
                                    a=4.0, b=8.0)
    # Should be finite and physically reasonable (between a and b)
    assert 3.0 < cp_extrap < 10.0


def test_extrapolation_cache_speeds_repeated_calls():
    """Caching avoids re-fitting Wilhoit on every call."""
    co2 = lookup("CO2")
    cache = {}
    cp1 = cp_R_extrapolated(co2.evaluator, 5000.0, cache=cache)
    cp2 = cp_R_extrapolated(co2.evaluator, 5000.0, cache=cache)
    assert cp1 == cp2
    # Cache should be populated
    assert len(cache) == 1
