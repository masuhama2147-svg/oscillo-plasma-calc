"""Plasma-formula round-trip checks."""
import math
import pytest

from oscillo_plasma_calc.plasma.boltzmann import electron_temperature_boltzmann
from oscillo_plasma_calc.plasma.debye import debye_length, plasma_frequency
from oscillo_plasma_calc.plasma.stark import electron_density_stark
from oscillo_plasma_calc.plasma.paschen import paschen_breakdown_voltage


def test_boltzmann_round_trip():
    # Fabricate a ratio that should recover Te = 1.0 eV
    Te_true = 1.0
    g_i = g_k = A_ij = A_kl = nu_ij = nu_kl = 1.0
    E_i, E_k = 12.0, 10.0
    dE = E_i - E_k
    ratio = math.exp(-dE / Te_true)     # prefactor=1 by construction
    tr = electron_temperature_boltzmann(
        ratio, 1.0, g_i, g_k, A_ij, A_kl, nu_ij, nu_kl, E_i, E_k,
    )
    assert tr.value == pytest.approx(Te_true, rel=1e-3)


def test_debye_and_plasma_freq_orders():
    # Te=1 eV, ne=1e18 m^-3  → λ_D ≈ 7.4e-6 m, f_p ≈ 9 GHz
    lam = debye_length(1.0, 1e18)
    assert 1e-7 < lam.value < 1e-4
    fp = plasma_frequency(1e18)
    assert 1e9 < fp.value < 1e11


def test_stark_monotone():
    n1 = electron_density_stark(0.1).value
    n2 = electron_density_stark(1.0).value
    assert n2 > n1


def test_paschen_positive_in_normal_range():
    vb = paschen_breakdown_voltage(101325.0, 1e-3).value
    assert math.isfinite(vb)
    assert vb > 0
