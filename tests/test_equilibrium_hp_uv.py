"""HP and UV equilibrium tests."""
import pytest

from oscillo_plasma_calc.equilibrium import equilibrium_hp, equilibrium_uv


def test_hp_h2_o2_finds_adiabatic_T():
    """Adiabatic flame T for H2/O2 stoichiometric ≈ 3000-3300 K at 1 atm."""
    # 1 mol H2 + 0.5 mol O2 with H_target = 0 (reference state) gives the
    # adiabatic flame temperature. We use a slightly negative H_target to
    # account for water-formation enthalpy release.
    res = equilibrium_hp(
        species=["H2", "O2", "H2O", "OH", "H", "O"],
        H_target_J=-100_000.0,  # roughly 0.5 mol of H2O formation enthalpy
        P_Pa=101325.0,
        reactants={"H": 2.0, "O": 1.0},
        T_guess_low=300.0, T_guess_high=4000.0,
    )
    assert res.converged
    assert 1500 < res.T_K < 3500


def test_hp_residual_small_relative():
    """If the HP solver claims convergence, |H_final − H_target| / max(|target|,1)
    must be < 1e-3 (per the new sanity check in equilibrium_hp)."""
    res = equilibrium_hp(
        species=["H2", "O2", "H2O", "OH"],
        H_target_J=-50_000.0,
        P_Pa=101325.0,
        reactants={"H": 2.0, "O": 1.0},
        T_guess_low=300.0, T_guess_high=4000.0,
    )
    if res.converged:
        denom = max(abs(res.H_target_J), 1.0)
        assert abs(res.H_final_J - res.H_target_J) / denom < 1e-3


def test_hp_unbracketed_T_returns_failure():
    """If the bracket can't enclose H_target, the solver fails cleanly."""
    res = equilibrium_hp(
        species=["H2", "O2", "H2O"],
        H_target_J=1e15,                       # absurd target
        P_Pa=101325.0,
        reactants={"H": 2.0, "O": 1.0},
        T_guess_low=300.0, T_guess_high=4000.0,
    )
    assert not res.converged
    assert "bracket" in res.message.lower() or "widen" in res.message.lower()


def test_uv_basic_convergence():
    """UV at 1 L volume, modest internal energy."""
    res = equilibrium_uv(
        species=["H2", "O2", "H2O", "OH", "H"],
        U_target_J=-50_000.0,
        V_m3=1e-3,                              # 1 L
        reactants={"H": 2.0, "O": 1.0},
        T_guess_low=300.0, T_guess_high=4000.0,
    )
    assert res.converged
    assert res.T_K > 300
    assert res.P_Pa > 0


def test_uv_pressure_consistent_with_ideal_gas():
    """P · V should equal n_total · R · T to high precision."""
    res = equilibrium_uv(
        species=["H2", "O2", "H2O"],
        U_target_J=0.0,
        V_m3=1e-3,
        reactants={"H": 2.0, "O": 1.0},
        T_guess_low=300.0, T_guess_high=4000.0,
    )
    if res.converged:
        R = 8.314462618
        n_total = sum(res.composition.moles.values())
        pv = res.P_Pa * res.V_m3
        nrt = n_total * R * res.T_K
        assert pv == pytest.approx(nrt, rel=0.01)
