"""Species dataclass for NASA PAC91 thermodynamic data."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Species:
    """A chemical species with NASA polynomial thermodynamic data.

    Attributes
    ----------
    name : str
        Conventional formula, e.g. "CO2", "H2O", "CH3OH".
    formula : dict[str, int]
        Element → atom count, e.g. {"C": 1, "O": 2} for CO2.
    molar_mass_g_per_mol : float
    Tmin : float
        Minimum valid temperature [K] for the polynomial.
    Tmax : float
        Maximum valid temperature [K].
    phase : str
        "gas", "liquid", "solid", or "graphite".
    source : str
        e.g. "NASA9-2002", "Burcat-2024", "GRI-Mech-3.0".
    notes : str
        Free-form notes (uncertainty, alternative forms, etc.).
    """

    name: str
    formula: dict[str, int]
    molar_mass_g_per_mol: float
    Tmin: float
    Tmax: float
    phase: str = "gas"
    source: str = ""
    notes: str = ""

    def is_in_temperature_range(self, T_K: float) -> bool:
        return self.Tmin <= T_K <= self.Tmax

    @property
    def element_set(self) -> frozenset[str]:
        return frozenset(self.formula.keys())
