"""Operational / budget / 1 kW rule tests."""
import pytest

from oscillo_plasma_calc.qa.operational import (
    device_power_budget, heat_dissipation_requirement, device_efficiency,
)


def test_budget_ok_when_half():
    tr = device_power_budget(400.0, budget_W=1000.0)
    assert tr.anomaly.level == "ok"
    assert tr.value == pytest.approx(60.0, rel=1e-3)


def test_budget_notice_edge():
    tr = device_power_budget(750.0, budget_W=1000.0)
    assert tr.anomaly.level == "notice"


def test_budget_warning_near_limit():
    tr = device_power_budget(950.0, budget_W=1000.0)
    assert tr.anomaly.level == "warning"


def test_budget_error_over():
    tr = device_power_budget(1200.0, budget_W=1000.0)
    assert tr.anomaly.level == "error"
    assert tr.value < 0


def test_heat_dissipation():
    tr = heat_dissipation_requirement(p_mean_W=1000.0, p_chem_W=100.0)
    assert tr.value == pytest.approx(900.0, rel=1e-3)


def test_device_efficiency():
    tr = device_efficiency(p_mean_W=800.0, w_socket_W=1000.0)
    assert tr.value == pytest.approx(80.0, rel=1e-3)
