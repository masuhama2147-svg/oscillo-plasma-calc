"""TP equilibrium tests with simple known cases."""
import pytest

from oscillo_plasma_calc.equilibrium import equilibrium_tp


def test_h2_o2_combustion_at_2000K():
    """H2 + 0.5 O2 → H2O at 2000K, 1 atm: H2O dominates but partial dissociation."""
    res = equilibrium_tp(
        species=["H2", "O2", "H2O", "OH", "H", "O"],
        T_K=2000.0,
        P_Pa=101325.0,
        reactants={"H": 2.0, "O": 1.0},
    )
    assert res.converged, f"failed: {res.message}"
    # Element balance should be tight
    assert res.element_balance_error < 1e-4
    # H2O is the dominant species
    assert res.mole_fractions["H2O"] > 0.5
    # Some dissociation products at 2000 K
    assert res.mole_fractions["H2"] > 0.0


def test_co2_h2_water_gas_shift_at_1000K():
    """CO2 + H2 ⇌ CO + H2O at 1000 K equilibrium."""
    res = equilibrium_tp(
        species=["CO2", "H2", "CO", "H2O"],
        T_K=1000.0,
        P_Pa=101325.0,
        reactants={"C": 1.0, "O": 2.0, "H": 2.0},
    )
    assert res.converged
    assert res.element_balance_error < 1e-4
    for name in ("CO2", "H2", "CO", "H2O"):
        assert res.mole_fractions[name] > 1e-6


def test_unknown_species_warned():
    res = equilibrium_tp(
        species=["NotARealSpecies", "H2", "O2", "H2O"],
        T_K=1500.0,
        P_Pa=101325.0,
        reactants={"H": 2.0, "O": 1.0},
    )
    assert res.converged
    assert any("NotARealSpecies" in w for w in res.warnings)


def test_too_few_species_returns_failure():
    res = equilibrium_tp(
        species=["JustOne"],
        T_K=1000.0,
        P_Pa=101325.0,
        reactants={"H": 1.0},
    )
    assert not res.converged


def test_temperature_out_of_range_warned():
    """Species outside its NASA range should be flagged."""
    res = equilibrium_tp(
        species=["CO2", "H2"],
        T_K=50.0,                  # below CO2/H2 Tmin
        P_Pa=101325.0,
        reactants={"C": 1.0, "O": 2.0, "H": 2.0},
    )
    assert not res.converged
    assert any("outside" in w for w in res.warnings)


def test_mole_fractions_sum_to_one():
    res = equilibrium_tp(
        species=["H2", "O2", "H2O", "OH"],
        T_K=1500.0,
        P_Pa=101325.0,
        reactants={"H": 2.0, "O": 1.0},
    )
    assert res.converged
    total = sum(res.mole_fractions.values())
    assert total == pytest.approx(1.0, abs=1e-6)
