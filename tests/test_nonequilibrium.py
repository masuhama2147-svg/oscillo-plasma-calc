"""Non-equilibrium plasma diagnostics tests."""
import math
import pytest

from oscillo_plasma_calc.plasma.nonequilibrium import (
    number_density_from_pt, reduced_electric_field, mean_electron_energy,
    non_equilibrium_ratio, vibrational_temperature_from_ratio,
)


def test_number_density_at_1atm_300K():
    n = number_density_from_pt(101325.0, 300.0)
    assert 2.4e25 < n < 2.5e25   # Loschmidt-like


def test_e_over_n_typical():
    # E = 3e6 V/m, 1 atm, 300 K → E/N ≈ 123 Td
    tr = reduced_electric_field(3e6, 101325.0, 300.0)
    assert 100 < tr.value < 150


def test_mean_e_energy_rises_with_EN():
    tr1 = mean_electron_energy(100.0)
    tr2 = mean_electron_energy(200.0)
    assert tr2.value > tr1.value


def test_non_eq_ratio():
    tr = non_equilibrium_ratio(T_e_K=1e4, T_gas_K=500.0)
    assert tr.value == pytest.approx(20.0, rel=1e-3)


def test_tvib_from_ratio():
    import math as m
    kB_eV = 1.380649e-23 / 1.602176634e-19  # eV/K
    # Manually: I_h/I_l = exp(-dE/(kB Tv))
    Tv_true = 3000.0
    dE = 0.291
    r = m.exp(-dE / (kB_eV * Tv_true))   # ~ 0.32
    tr = vibrational_temperature_from_ratio(I_high=r, I_low=1.0, dE_vib_eV=dE)
    assert tr.value == pytest.approx(Tv_true, rel=1e-3)
