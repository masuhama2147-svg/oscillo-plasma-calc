"""G1-G6 research-decision gate tests."""
from dataclasses import dataclass
from oscillo_plasma_calc.qa import evaluate_gates


@dataclass
class _MockValidation:
    passed: bool
    hard_errors: list = None
    warnings: list = None
    def __post_init__(self):
        self.hard_errors = self.hard_errors or []
        self.warnings = self.warnings or []


@dataclass
class _MockTrace:
    value: float = 0.0
    def scalar(self):
        return self.value


@dataclass
class _MockBundle:
    energy: object = None


@dataclass
class _MockBP:
    is_te_reliable: bool
    r_squared: float = 0.9
    n_used: int = 3
    Te_K: float = 10000.0
    reliability_warning: str = ""


def test_all_locked_when_no_data():
    gates = evaluate_gates()
    assert all(not g.passed for g in gates)
    assert gates[0].blocker  # G1 has blocker text


def test_g1_passes_when_validation_passes():
    val = _MockValidation(passed=True)
    gates = evaluate_gates(validation=val)
    assert gates[0].passed
    assert gates[0].name == "G1 Data Valid"


def test_g1_fails_with_hard_errors():
    from oscillo_plasma_calc.qa.csv_validator import ValidationItem
    val = _MockValidation(passed=False, hard_errors=[ValidationItem("error", "missing column voltage_V")])
    gates = evaluate_gates(validation=val)
    assert not gates[0].passed
    assert "missing column" in gates[0].blocker


def test_g2_locked_without_bundle():
    val = _MockValidation(passed=True)
    gates = evaluate_gates(validation=val, bundle=None)
    assert not gates[1].passed
    assert gates[1].severity == "locked"


def test_g2_provisional_when_energy_too_small():
    val = _MockValidation(passed=True)
    bundle = _MockBundle(energy=_MockTrace(value=1e-7))   # 0.1 μJ
    gates = evaluate_gates(validation=val, bundle=bundle)
    assert not gates[1].passed
    assert gates[1].severity == "provisional"


def test_g2_passes_with_realistic_energy():
    val = _MockValidation(passed=True)
    bundle = _MockBundle(energy=_MockTrace(value=0.018))  # 18 mJ
    gates = evaluate_gates(validation=val, bundle=bundle)
    assert gates[1].passed


def test_g3_provisional_when_te_unreliable():
    val = _MockValidation(passed=True)
    bundle = _MockBundle(energy=_MockTrace(value=0.018))
    bp = _MockBP(is_te_reliable=False, r_squared=0.6, n_used=3,
                 reliability_warning="R² = 0.600 < 0.85")
    gates = evaluate_gates(validation=val, bundle=bundle, spec_bp=bp)
    assert not gates[2].passed
    assert gates[2].severity == "provisional"


def test_g3_passes_when_reliable():
    val = _MockValidation(passed=True)
    bundle = _MockBundle(energy=_MockTrace(value=0.018))
    bp = _MockBP(is_te_reliable=True, r_squared=0.97, n_used=4, Te_K=15000)
    gates = evaluate_gates(validation=val, bundle=bundle, spec_bp=bp)
    assert gates[2].passed


def test_g4_locked_when_g3_fails():
    """Cascading lock: G4 cannot pass without G3."""
    val = _MockValidation(passed=True)
    bundle = _MockBundle(energy=_MockTrace(value=0.018))
    bp = _MockBP(is_te_reliable=False, r_squared=0.6, n_used=2)
    gates = evaluate_gates(validation=val, bundle=bundle, spec_bp=bp)
    assert not gates[3].passed
    assert "G3" in gates[3].blocker


def test_g6_summarizes_all():
    gates = evaluate_gates()
    g6 = gates[5]
    assert g6.name == "G6 Research Valid"
    assert not g6.passed
    assert "未通過" in g6.blocker


def test_gate_returns_six_in_order():
    gates = evaluate_gates()
    names = [g.name for g in gates]
    assert names == [
        "G1 Data Valid", "G2 Energy Valid", "G3 Te Valid",
        "G4 Thermo Valid", "G5 Equilibrium Valid", "G6 Research Valid",
    ]
