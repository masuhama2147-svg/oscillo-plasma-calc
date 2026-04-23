"""Tests for advanced electrical quantities (pulse energy, duty, crest/form, etc)."""
import math
import numpy as np
import pytest

from oscillo_plasma_calc.electrical.advanced import (
    detect_pulses, pulse_energy, duty_cycle, effective_average_power,
    abs_power_mean, crest_factor, form_factor, power_density,
)


def _gaussian_pulse_train(n_pulses=4, fs_MHz=500, window_us=20,
                           pulse_fwhm_ns=100, V0=10000, I0=20):
    dt = 1.0 / (fs_MHz * 1e6)
    n = int(window_us * 1e-6 / dt)
    t = np.arange(n) * dt
    v = np.zeros(n); i = np.zeros(n)
    centers = np.linspace(2e-6, (window_us - 2) * 1e-6, n_pulses)
    sigma = pulse_fwhm_ns * 1e-9 / (2 * math.sqrt(2 * math.log(2)))
    for c in centers:
        v += V0 * np.exp(-((t - c)**2) / (2 * sigma ** 2))
        i += I0 * np.exp(-((t - c)**2) / (2 * sigma ** 2))
    return t, v, i


def test_detect_pulses_counts_4():
    t, v, _ = _gaussian_pulse_train(n_pulses=4)
    peaks, fwhm, n = detect_pulses(t, v)
    assert n == 4
    assert 50e-9 < fwhm < 200e-9   # ~100 ns FWHM


def test_pulse_energy_returns_1_over_N_of_window():
    from scipy.integrate import trapezoid
    t, v, i = _gaussian_pulse_train(n_pulses=4)
    tr = pulse_energy(t, v, i)
    e_win = float(trapezoid(v * i, t))
    assert tr.value == pytest.approx(e_win / 4, rel=1e-3)
    assert tr.unit == "J"


def test_duty_cycle_reasonable():
    t, v, _ = _gaussian_pulse_train(n_pulses=4, pulse_fwhm_ns=100)
    tr = duty_cycle(t, v)
    # 4 pulses × 100 ns / 20 μs = 2 %
    assert 0.005 < tr.value < 0.1


def test_effective_average_power_scales_with_duty():
    V0, I0 = 10000, 20
    t, v, i = _gaussian_pulse_train(n_pulses=4, V0=V0, I0=I0)
    tr = effective_average_power(v, i, duty=0.02)
    peak = V0 * I0     # in-phase gaussians
    assert tr.value == pytest.approx(peak * 0.02, rel=0.1)


def test_crest_factor_sine_is_sqrt2():
    t = np.linspace(0, 1, 10000, endpoint=False)
    v = np.sin(2 * np.pi * 5 * t)
    tr = crest_factor(v)
    assert tr.value == pytest.approx(math.sqrt(2), rel=1e-3)


def test_form_factor_sine():
    t = np.linspace(0, 1, 10000, endpoint=False)
    v = np.sin(2 * np.pi * 5 * t)
    tr = form_factor(v)
    assert tr.value == pytest.approx(math.pi / (2 * math.sqrt(2)), rel=1e-2)


def test_abs_power_mean_positive():
    t, v, i = _gaussian_pulse_train(n_pulses=3)
    tr = abs_power_mean(t, v, i)
    assert tr.value > 0


def test_power_density_with_volume():
    tr = power_density(p_mean_W=1000.0, volume_m3=1e-6)
    assert tr.value == pytest.approx(1e9, rel=1e-3)  # 1 GW/m^3
