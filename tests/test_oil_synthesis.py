"""Oil-synthesis KPI tests."""
import pytest

from oscillo_plasma_calc.chemistry.oil_synthesis import (
    specific_energy_input, energy_cost, co2_conversion_rate,
    single_pass_energy_efficiency, asf_chain_probability,
)


def test_sei_basic():
    # 300 kJ per mol
    tr = specific_energy_input(E_plasma_J=300.0, n_CO2_mol=1e-3)
    assert tr.value == pytest.approx(300.0, rel=1e-3)
    assert tr.unit == "kJ/mol"


def test_energy_cost_basic():
    tr = energy_cost(E_plasma_J=500.0, n_product_mol=1e-3)
    assert tr.value == pytest.approx(500.0, rel=1e-3)


def test_co2_conversion_10pct():
    tr = co2_conversion_rate(n_CO2_in_mol=1.0, n_CO2_out_mol=0.9)
    assert tr.value == pytest.approx(10.0, rel=1e-3)


def test_eta_se_consistency():
    # χ=10 %, ΔH=283 kJ/mol (CO2→CO), SEI=1000 kJ/mol → η=2.83 %
    tr = single_pass_energy_efficiency(10.0, 283.0, 1000.0)
    assert tr.value == pytest.approx(2.83, rel=1e-3)


def test_asf_recovers_alpha():
    # Proper ASF: weight fraction W_n ∝ n · α^n
    #   → ln(W_n / n) = n · ln(α) + const, fitting recovers α exactly.
    alpha_true = 0.85
    dist = {n: n * (alpha_true ** n) for n in range(1, 8)}
    tr = asf_chain_probability(dist)
    assert tr.value == pytest.approx(alpha_true, rel=5e-3)
