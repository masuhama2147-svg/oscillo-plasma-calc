"""Cantera-YAML thermodynamic database loader.

Reads the bundled `data/thermo/*.yaml` files (downloaded from the
Cantera project, MIT licensed) and exposes a unified `lookup(name)`
returning either a `NASA7` or `NASA9` evaluator + Species metadata.

Datasets currently bundled
--------------------------
- `gri30.yaml`        — GRI-Mech 3.0 (53 species, CH4 combustion)
- `airNASA9.yaml`     — Air species (11) NASA9 form
- `nasa_gas.yaml`     — NASA Glenn 2002 gas species (748)
- `nasa_condensed.yaml` — NASA Glenn 2002 condensed phases (382)

Lookup strategy: gri30 → nasa_gas → nasa_condensed (first match wins).
The user can override with `lookup(name, dataset="nasa_gas")` to
disambiguate (e.g. CO2 has slightly different ranges in gri30 vs nasa_gas).

The YAML files are loaded lazily on first call and cached.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from .nasa_poly import NASA7, NASA7Range, NASA9, NASA9Range
from .species import Species

# Resolve the project-root data dir relative to this file.
# This file:  .../src/oscillo_plasma_calc/thermo/database.py
# Project:    .../  (3 parents up)
_DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "thermo"

# Datasets in fallback order.
_DATASETS = ("gri30.yaml", "nasa_gas.yaml", "airNASA9.yaml", "nasa_condensed.yaml")


@dataclass(frozen=True)
class SpeciesEntry:
    """A species record with its evaluator (NASA7 or NASA9)."""
    species: Species
    evaluator: NASA7 | NASA9
    dataset: str       # "gri30.yaml" etc.


def _yaml_path(name: str) -> Path:
    return _DATA_DIR / name


def _build_nasa7(name: str, thermo: dict) -> NASA7 | None:
    """Build a NASA7 evaluator from Cantera YAML thermo block.

    Cantera YAML has `temperature-ranges` of length N+1 and `data` of length N
    (each entry = 7-coefficient list). We support N == 1 or 2.
    """
    ranges = thermo["temperature-ranges"]
    data = thermo["data"]
    if len(data) == 1:
        # Single range — duplicate it as both low and high so the evaluator's
        # "low or high" branching becomes a no-op.
        Tmin, Tmax = ranges[0], ranges[1]
        a = tuple(data[0])
        rng = NASA7Range(Tmin=Tmin, Tmax=Tmax, a=a)
        return NASA7(name=name, low=rng, high=rng)
    if len(data) == 2:
        Tmin, Tmid, Tmax = ranges[0], ranges[1], ranges[2]
        return NASA7(
            name=name,
            low=NASA7Range(Tmin=Tmin, Tmax=Tmid, a=tuple(data[0])),
            high=NASA7Range(Tmin=Tmid, Tmax=Tmax, a=tuple(data[1])),
        )
    return None


def _build_nasa9(name: str, thermo: dict) -> NASA9 | None:
    """Build a NASA9 evaluator. NASA9 entries store [a1..a7, b1, b2] = 9 numbers."""
    ranges = thermo["temperature-ranges"]
    data = thermo["data"]
    if len(data) != len(ranges) - 1:
        return None
    rngs = []
    for i, coeffs in enumerate(data):
        if len(coeffs) != 9:
            return None
        a = tuple(coeffs[:7])
        b = (float(coeffs[7]), float(coeffs[8]))
        rngs.append(NASA9Range(Tmin=ranges[i], Tmax=ranges[i + 1], a=a, b=b))
    return NASA9(name=name, ranges=tuple(rngs))


_ELEMENT_MASS = {
    "H": 1.00794, "He": 4.002602,
    "C": 12.0107, "N": 14.0067, "O": 15.9994, "F": 18.9984032,
    "Ne": 20.1797, "Na": 22.989770, "Mg": 24.3050, "Al": 26.9815386,
    "Si": 28.0855, "P": 30.973762, "S": 32.065, "Cl": 35.453, "Ar": 39.948,
    "K": 39.0983, "Ca": 40.078, "Fe": 55.845, "Cu": 63.546,
    "W": 183.84, "Au": 196.96655,
    "E": 5.485799e-4,    # electron (g/mol equivalent of m_e)
}


def _molar_mass_g_per_mol(formula: dict[str, int]) -> float:
    M = 0.0
    for el, n in formula.items():
        M += _ELEMENT_MASS.get(el, 0.0) * n
    return M


def _coerce_name(raw: Any) -> str:
    """Recover species names that PyYAML 1.1 silently coerced to bool / None.

    `NO` (nitric oxide), `Yes`/`No`/`On`/`Off`/`Y`/`N` are all YAML 1.1
    boolean tokens, and `NULL` becomes None. We map them back to the
    chemistry convention used by Cantera / NASA datasets.
    """
    if raw is True:
        return "YES"
    if raw is False:
        return "NO"
    if raw is None:
        return "NULL"
    return str(raw)


def _entry_from_record(rec: dict[str, Any], dataset: str) -> SpeciesEntry | None:
    name = _coerce_name(rec["name"])
    formula = rec.get("composition", {})
    thermo = rec.get("thermo", {})
    model = thermo.get("model")

    if model == "NASA7":
        evaluator = _build_nasa7(name, thermo)
    elif model == "NASA9":
        evaluator = _build_nasa9(name, thermo)
    else:
        return None
    if evaluator is None:
        return None

    ranges = thermo["temperature-ranges"]
    note = thermo.get("note", "")
    species = Species(
        name=name,
        formula={k: int(v) for k, v in formula.items()},
        molar_mass_g_per_mol=_molar_mass_g_per_mol(
            {k: int(v) for k, v in formula.items()}
        ),
        Tmin=float(ranges[0]),
        Tmax=float(ranges[-1]),
        phase="condensed" if "condensed" in dataset else "gas",
        source=f"{dataset} {note}".strip(),
    )
    return SpeciesEntry(species=species, evaluator=evaluator, dataset=dataset)


@lru_cache(maxsize=8)
def _load_dataset(name: str) -> dict[str, SpeciesEntry]:
    """Lazily load a single YAML dataset into a name → SpeciesEntry map."""
    path = _yaml_path(name)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    out: dict[str, SpeciesEntry] = {}
    for rec in doc.get("species", []):
        entry = _entry_from_record(rec, dataset=name)
        if entry is not None:
            out[entry.species.name] = entry
    return out


def available_datasets() -> list[str]:
    """Return the list of dataset filenames that are physically present."""
    return [name for name in _DATASETS if _yaml_path(name).exists()]


def list_species(dataset: str | None = None) -> list[str]:
    """Return sorted species names from one or all datasets."""
    if dataset is not None:
        return sorted(_load_dataset(dataset).keys())
    seen: set[str] = set()
    for ds in _DATASETS:
        seen.update(_load_dataset(ds).keys())
    return sorted(seen)


def lookup(name: str, dataset: str | None = None) -> SpeciesEntry | None:
    """Return a SpeciesEntry for `name`. Searches datasets in fallback order
    unless an explicit `dataset` is requested.
    """
    if dataset is not None:
        return _load_dataset(dataset).get(name)
    for ds in _DATASETS:
        entry = _load_dataset(ds).get(name)
        if entry is not None:
            return entry
    return None


def species_count() -> dict[str, int]:
    """Diagnostic: per-dataset species counts."""
    return {ds: len(_load_dataset(ds)) for ds in available_datasets()}
