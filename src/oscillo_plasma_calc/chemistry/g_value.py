"""G-value: molecules produced per 100 eV of absorbed energy.

Reference: 2012_IJHE-37-16000, 2020_JJIE_99-104 (Nomura-lab hydrogen yield studies).
"""
from __future__ import annotations

from ..config.constants import J_TO_EV
from ..report.trace import TraceResult
from ..report.ui_format import pretty_number


def g_value(n_product_mol: float, E_absorbed_J: float) -> TraceResult:
    E_eV = E_absorbed_J * J_TO_EV
    if E_eV <= 0:
        return TraceResult(name="G value",
                           value=float("nan"), unit="molecules/100 eV",
                           equation_latex=r"G = n_\mathrm{prod}/(E_\mathrm{abs}/100)")
    N_molecules = n_product_mol * 6.02214076e23
    G = N_molecules / (E_eV / 100.0)
    return TraceResult(
        name="G value (yield per 100 eV)",
        value=G, unit="molecules/100 eV",
        equation_latex=r"G = \frac{N_\mathrm{prod}}{E_\mathrm{abs}/100\,\text{eV}}",
        substitution_latex=(
            fr"G = \frac{{{pretty_number(N_molecules)}}}"
            fr"{{{pretty_number(E_eV)}/100}} "
            fr"= {pretty_number(G)}\,\text{{molecules / 100 eV}}"
        ),
        steps=[
            f"n_product = {n_product_mol:.4g} mol → {N_molecules:.4g} molecules",
            f"E_absorbed = {E_absorbed_J:.4g} J = {E_eV:.4g} eV",
        ],
        sources=["2012_IJHE-37-16000", "2020_JJIE_99-104"],
    )
