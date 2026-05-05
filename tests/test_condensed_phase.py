"""Condensed-phase insertion test."""
from oscillo_plasma_calc.equilibrium import (
    evaluate_condensed_insertion, DEFAULT_CANDIDATES,
)
from oscillo_plasma_calc.equilibrium.condensed_phase import _filter_known


def test_default_candidates_resolvable():
    """At least some default condensed candidates must exist in the DB."""
    found = _filter_known(DEFAULT_CANDIDATES)
    assert len(found) >= 3, f"only {found} found, expected ≥ 3"


def test_carbon_no_insertion_when_no_carbon_input():
    """No C in reactants → no graphite insertion, regardless of T."""
    result = evaluate_condensed_insertion(
        gas_species=["H2", "O2", "H2O", "OH"],
        T_K=2000.0,
        P_Pa=101325.0,
        reactants={"H": 2.0, "O": 1.0},
    )
    # The C-containing candidates should all be rejected since there is
    # no carbon in the element balance to populate them.
    assert "C(gr)" not in result.inserted


def test_clean_h2o2_no_condensed_at_2000K():
    """Pure H2/O2 at 2000 K, 1 atm → no condensed phase expected."""
    result = evaluate_condensed_insertion(
        gas_species=["H2", "O2", "H2O", "OH", "H", "O"],
        T_K=2000.0,
        P_Pa=101325.0,
        reactants={"H": 2.0, "O": 1.0},
    )
    # Should not insert anything
    assert len(result.inserted) == 0


def test_insertion_test_returns_structure():
    """API smoke test: returns inserted, rejected, gas_only, final, delta_gibbs."""
    result = evaluate_condensed_insertion(
        gas_species=["H2", "O2", "H2O"],
        T_K=1000.0,
        P_Pa=101325.0,
        reactants={"H": 2.0, "O": 1.0},
    )
    assert hasattr(result, "inserted")
    assert hasattr(result, "rejected")
    assert hasattr(result, "gas_only")
    assert hasattr(result, "final")
    assert hasattr(result, "delta_gibbs_RT")
