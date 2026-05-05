"""EEDF / two-term Boltzmann / LXCat parser tests."""
import numpy as np
import pytest

from oscillo_plasma_calc.plasma.eedf import (
    maxwell_eedf, druyvesteyn_eedf, mean_energy_from_eedf,
    solve_two_term, parse_lxcat,
)


def test_maxwell_normalisation():
    """Maxwell EEDF should integrate to 1 (within 5% on a finite grid)."""
    eps = np.linspace(1e-6, 100, 2000)
    f = maxwell_eedf(eps, mean_energy_eV=2.0)
    norm = np.trapezoid(f * np.sqrt(eps), eps)
    assert norm == pytest.approx(1.0, rel=0.02)


def test_maxwell_round_trip_mean_energy():
    """Recover the mean energy back from the EEDF with a fine enough grid."""
    eps = np.linspace(1e-6, 100, 2000)
    for mean_eV in (1.0, 2.0, 5.0):
        f = maxwell_eedf(eps, mean_eV)
        recovered = mean_energy_from_eedf(eps, f)
        # Trapezoidal grid noise + truncation: 5% tolerance
        assert recovered == pytest.approx(mean_eV, rel=0.05)


def test_druyvesteyn_normalisation():
    eps = np.linspace(1e-6, 30, 500)
    f = druyvesteyn_eedf(eps, mean_energy_eV=2.0)
    norm = np.trapezoid(f * np.sqrt(eps), eps)
    assert norm == pytest.approx(1.0, rel=0.05)


def test_two_term_constant_xs_runs():
    """Constant elastic cross section: solver should converge."""
    Q_const = lambda e: 1e-19
    res = solve_two_term(
        EN_Td=50.0,
        momentum_xs=Q_const,
        M_amu=28.0,
        T_gas_K=300.0,
        eps_max_eV=20.0,
        n_grid=100,
    )
    assert res.converged
    # Mean energy in a sensible range
    assert 0.1 < res.mean_energy_eV < 30.0
    norm = np.trapezoid(res.f0 * np.sqrt(res.eps_eV), res.eps_eV)
    assert norm == pytest.approx(1.0, rel=0.05)


def test_two_term_high_EN_warning():
    Q_const = lambda e: 1e-19
    res = solve_two_term(
        EN_Td=2000.0, momentum_xs=Q_const, eps_max_eV=50.0,
    )
    assert any("high" in w.lower() or "two-term" in w.lower()
               for w in res.warnings)


def test_two_term_inelastic_rate_zero_below_threshold():
    Q_const = lambda e: 1e-19
    Q_excite = lambda e: 1e-20
    threshold = 100.0   # very high, EEDF won't reach it at low E/N
    res = solve_two_term(
        EN_Td=10.0,
        momentum_xs=Q_const,
        inelastic_xs={"excite_high": (threshold, Q_excite)},
        eps_max_eV=20.0,
    )
    # Rate coefficient should be tiny because EEDF doesn't extend to 100 eV
    assert res.rate_coefficients["excite_high"] < 1e-25


_LXCAT_SAMPLE = """COMMENT: Synthetic test data
PROCESS: e + N2 -> e + N2 (ELASTIC)
SPECIES: e / N2
PROCESS_TYPE: ELASTIC
THRESHOLD: 0.0 eV
COLUMNS: Energy (eV) | Cross section (m^2)
-----------------------------
0.0  1.000e-20
1.0  1.500e-20
10.0 1.200e-20
-----------------------------
PROCESS: e + N2 -> e + N2(v=1) (EXCITATION)
SPECIES: e / N2
PROCESS_TYPE: EXCITATION
THRESHOLD: 0.29 eV
COLUMNS: Energy (eV) | Cross section (m^2)
-----------------------------
0.29 0.0
1.0  3.000e-22
5.0  5.000e-22
-----------------------------
"""


def test_lxcat_parser_two_blocks():
    xs = parse_lxcat(_LXCAT_SAMPLE)
    assert len(xs) == 2
    assert xs[0].process_type == "ELASTIC"
    assert xs[1].process_type == "EXCITATION"
    assert xs[1].threshold_eV == pytest.approx(0.29, rel=1e-3)


def test_lxcat_interpolation_below_threshold_zero():
    xs = parse_lxcat(_LXCAT_SAMPLE)
    excite = xs[1]
    assert excite.at(0.1) == 0.0          # below threshold
    assert excite.at(1.0) == pytest.approx(3e-22, rel=1e-3)
    # midpoint
    midpoint = excite.at(3.0)
    assert 3e-22 < midpoint < 5e-22


def test_lxcat_at_above_max_energy_clamped():
    xs = parse_lxcat(_LXCAT_SAMPLE)
    elastic = xs[0]
    assert elastic.at(1000.0) == pytest.approx(elastic.sigmas_m2[-1])
