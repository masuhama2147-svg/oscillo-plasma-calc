"""Verify Te from Boltzmann plot matches the xlsx spreadsheet exactly."""
import pytest

from oscillo_plasma_calc.spectroscopy import (
    excitation_temperature, load_intensity_csv, save_intensity_template,
    list_elements,
)


@pytest.mark.parametrize("element, intensities, Te_expected", [
    # Values hand-computed from `励起温度計算シート ver.2.xlsx` formulas.
    ("H",  {"Halpha": 16473.9, "Hbeta": 5291.44, "Hgamma": 1272.68}, 10_800),
    ("O",  {"O1": 24888.9, "O4": 9623.82},                           3_999),
    ("W",  {"W1": 3319, "W2": 2920, "W3": 4487, "W4": 2620},         7_989),
    ("Al", {"Al2": 78437.3, "Al4": 56310.4},                         7_409),
    ("Cu", {"Cu1": 22329, "Cu2": 18745},                              662),
])
def test_te_matches_xlsx(element, intensities, Te_expected):
    res, tr = excitation_temperature(element, intensities)
    assert res.Te_K == pytest.approx(Te_expected, rel=5e-3)
    assert tr.unit == "K"
    assert tr.sources   # non-empty


def test_excluded_zero_lines():
    res, _ = excitation_temperature(
        "H", {"Halpha": 16473.9, "Hbeta": 5291.44, "Hgamma": 0.0})
    assert res.n_used == 2
    assert "Hgamma" in res.excluded


def test_missing_element_raises():
    with pytest.raises(KeyError):
        excitation_temperature("Xe", {"X1": 1.0})


def test_known_elements_list():
    assert {"H", "O", "W", "Al", "Cu"} <= set(list_elements())


def test_template_and_load_round_trip(tmp_path):
    path = tmp_path / "tpl.csv"
    save_intensity_template("H", path)
    # Fill in Halpha only
    text = path.read_text().replace("Halpha,0", "Halpha,100.0")
    path.write_text(text)
    grouped, meta = load_intensity_csv(path)
    assert meta["element"] == "H"
    assert grouped["H"]["Halpha"] == 100.0
    assert grouped["H"]["Hbeta"] == 0.0
