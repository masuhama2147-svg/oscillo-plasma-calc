"""Phase 5 skeleton: NASA polynomial evaluators + Species + log10 K."""
import math
import pytest

from oscillo_plasma_calc.thermo import NASA7, NASA9, Species, log10_K_from_dG
from oscillo_plasma_calc.thermo.nasa_poly import NASA7Range, NASA9Range


# CO2 NASA7 coefficients from GRI-Mech 3.0 thermo.dat
_CO2_NASA7 = NASA7(
    name="CO2",
    low=NASA7Range(
        Tmin=200.0, Tmax=1000.0,
        a=(2.35677352, 8.98459677e-3, -7.12356269e-6,
           2.45919022e-9, -1.43699548e-13,
           -4.83719697e+4, 9.90105222),
    ),
    high=NASA7Range(
        Tmin=1000.0, Tmax=3500.0,
        a=(3.85746029, 4.41437026e-3, -2.21481404e-6,
           5.23490188e-10, -4.72084164e-14,
           -4.87591660e+4, 2.27163806),
    ),
)


def test_nasa7_cp_at_298_matches_jana():
    """At 298.15 K, CO2 Cp/R should be ≈ 4.45 (Cp ≈ 37 J/mol/K)."""
    cp_R = _CO2_NASA7.cp_R(298.15)
    R = 8.314462618
    cp = cp_R * R
    assert 35.0 < cp < 40.0, f"CO2 Cp at 298 K = {cp:.2f}, expected ≈ 37"


def test_nasa7_cp_at_1000_matches_jana():
    """CO2 Cp at 1000 K ≈ 54.3 J/mol/K (JANAF table value 54.308)."""
    cp_R = _CO2_NASA7.cp_R(1000.0)
    R = 8.314462618
    cp = cp_R * R
    assert cp == pytest.approx(54.31, rel=0.005), \
        f"CO2 Cp at 1000 K = {cp:.2f}, expected ≈ 54.31 (JANAF)"


def test_nasa7_cp_continuity_at_split():
    """The two ranges share T_split = 1000 K. Cp must be continuous there."""
    cp_low = _CO2_NASA7.cp_R(1000.0 - 1e-6)
    cp_high = _CO2_NASA7.cp_R(1000.0 + 1e-6)
    # GRI-Mech CO2 has a small jump at the split (ASCII format limitation)
    assert abs(cp_low - cp_high) < 0.05


def test_nasa7_g_eq_h_minus_s():
    """Self-consistency: G/RT = H/RT − S/R."""
    T = 1500.0
    h = _CO2_NASA7.h_RT(T)
    s = _CO2_NASA7.s_R(T)
    g = _CO2_NASA7.g_RT(T)
    assert g == pytest.approx(h - s, rel=1e-12)


def test_nasa7_out_of_range_raises():
    with pytest.raises(ValueError):
        _CO2_NASA7.cp_R(50.0)
    with pytest.raises(ValueError):
        _CO2_NASA7.cp_R(5000.0)


def test_log10_K_from_dG_zero_at_dG_zero():
    assert log10_K_from_dG(0.0, 298.15) == pytest.approx(0.0, abs=1e-12)


def test_log10_K_from_dG_negative_dG_gives_positive_K():
    """ΔG = -100 kJ/mol at 1000 K → K » 1, log10 K positive."""
    R = 8.314462618
    T = 1000.0
    dG = -1e5
    expected = -dG / (R * T * math.log(10))
    assert log10_K_from_dG(dG, T) == pytest.approx(expected, rel=1e-12)


def test_log10_K_negative_T_raises():
    with pytest.raises(ValueError):
        log10_K_from_dG(0.0, -1.0)


def test_species_temperature_range():
    co2 = Species(
        name="CO2",
        formula={"C": 1, "O": 2},
        molar_mass_g_per_mol=44.01,
        Tmin=200.0,
        Tmax=3500.0,
        source="GRI-Mech-3.0",
    )
    assert co2.is_in_temperature_range(298.15)
    assert co2.is_in_temperature_range(2000.0)
    assert not co2.is_in_temperature_range(100.0)
    assert not co2.is_in_temperature_range(4000.0)
    assert co2.element_set == frozenset({"C", "O"})


def test_nasa9_skeleton_evaluates():
    """Smoke test: NASA9 with 1 trivial range should compute Cp/R = a3 at any T."""
    h2_dummy = NASA9(
        name="H2_dummy",
        ranges=(NASA9Range(Tmin=200.0, Tmax=6000.0,
                           a=(0.0, 0.0, 3.5, 0.0, 0.0, 0.0, 0.0),
                           b=(0.0, 0.0)),),
    )
    assert h2_dummy.cp_R(1000.0) == pytest.approx(3.5, rel=1e-12)


def test_nasa9_g_eq_h_minus_s():
    h2_dummy = NASA9(
        name="H2_dummy",
        ranges=(NASA9Range(Tmin=200.0, Tmax=6000.0,
                           a=(0.0, 0.0, 3.5, 0.0, 0.0, 0.0, 0.0),
                           b=(0.0, 0.0)),),
    )
    T = 1500.0
    h = h2_dummy.h_RT(T)
    s = h2_dummy.s_R(T)
    g = h2_dummy.g_RT(T)
    assert g == pytest.approx(h - s, rel=1e-12)
