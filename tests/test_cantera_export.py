"""Cantera YAML export tests."""
import yaml
import pytest

from oscillo_plasma_calc.thermo import export_cantera_yaml


def test_basic_export_round_trips():
    """Export 3 species and confirm Cantera-style YAML structure."""
    text = export_cantera_yaml(["CO2", "H2", "H2O"])
    doc = yaml.safe_load(text)
    assert "phases" in doc
    assert "species" in doc
    assert len(doc["species"]) == 3
    species_names = [s["name"] for s in doc["species"]]
    assert "CO2" in species_names and "H2" in species_names


def test_phase_metadata_present():
    text = export_cantera_yaml(["CO2", "H2", "H2O"], phase_name="plasma")
    doc = yaml.safe_load(text)
    p = doc["phases"][0]
    assert p["name"] == "plasma"
    assert p["thermo"] == "ideal-gas"
    assert "C" in p["elements"]
    assert "H" in p["elements"]
    assert "O" in p["elements"]


def test_species_thermo_block_has_nasa_format():
    text = export_cantera_yaml(["CO2"])
    doc = yaml.safe_load(text)
    co2 = doc["species"][0]
    assert co2["thermo"]["model"] in ("NASA7", "NASA9")
    assert "temperature-ranges" in co2["thermo"]
    assert "data" in co2["thermo"]


def test_unknown_species_recorded_as_skipped():
    text = export_cantera_yaml(["CO2", "NotARealSpecies"])
    doc = yaml.safe_load(text)
    assert "skipped_species_not_in_db" in doc
    assert "NotARealSpecies" in doc["skipped_species_not_in_db"]


def test_write_to_file(tmp_path):
    from oscillo_plasma_calc.thermo import write_cantera_yaml
    out = tmp_path / "out.yaml"
    path = write_cantera_yaml(["H2", "O2", "H2O"], out)
    assert out.exists()
    text = out.read_text()
    assert "species:" in text


def test_exported_yaml_loadable_by_cantera_if_available():
    """If Cantera is installed, the exported YAML must load without error."""
    pytest.importorskip("cantera")
    import cantera as ct
    text = export_cantera_yaml(["H2", "O2", "H2O", "OH", "H", "O"])
    # Cantera 3.x can load directly from YAML string
    sol = ct.Solution(yaml=text)
    assert sol.n_species == 6
