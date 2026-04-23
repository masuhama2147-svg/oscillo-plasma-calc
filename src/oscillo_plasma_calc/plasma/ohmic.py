"""Volumetric Ohmic heating density: p_ohm = σ E^2.

Reference: 2011_PSST-20-034016 (effect of liquid conductivity).
"""
from __future__ import annotations

from ..report.trace import TraceResult
from ..report.ui_format import pretty_number


def ohmic_heating_density(sigma_Sm: float, E_Vm: float) -> TraceResult:
    p = sigma_Sm * E_Vm ** 2
    return TraceResult(
        name="Ohmic heating density p_ohm",
        value=p, unit="W/m^3",
        equation_latex=r"p_\mathrm{ohm} = \sigma E^2",
        substitution_latex=(
            fr"p_\mathrm{{ohm}} = {pretty_number(sigma_Sm)}\,\text{{S/m}} "
            fr"\times ({pretty_number(E_Vm)}\,\text{{V/m}})^2 "
            fr"= {pretty_number(p)}\,\text{{W/m}}^3"
        ),
        sources=["2011_PSST-20-034016"],
    )
