"""Chemical energy-conversion efficiency η = ΔH · n / E_plasma."""
from __future__ import annotations

from ..report.trace import TraceResult
from ..report.ui_format import format_si, pretty_number


def chemical_efficiency(delta_H_kJ_per_mol: float,
                        n_product_mol: float,
                        E_plasma_J: float) -> TraceResult:
    if E_plasma_J <= 0:
        return TraceResult(name="Chemical efficiency η",
                           value=float("nan"), unit="%",
                           equation_latex=r"\eta = \Delta H \cdot n/E_\mathrm{plasma}")
    E_chem_J = delta_H_kJ_per_mol * 1000.0 * n_product_mol
    eta = 100.0 * E_chem_J / E_plasma_J
    return TraceResult(
        name="Chemical energy-conversion efficiency η",
        value=eta, unit="%",
        equation_latex=(
            r"\eta_\mathrm{chem} = "
            r"\frac{\Delta H\,n_\mathrm{prod}}{E_\mathrm{plasma}}\times 100\%"
        ),
        substitution_latex=(
            fr"\eta = \frac{{{pretty_number(delta_H_kJ_per_mol)}\,\text{{kJ/mol}}"
            fr" \times {pretty_number(n_product_mol)}\,\text{{mol}}}}"
            fr"{{{format_si(E_plasma_J, 'J')}}}\times 100\% "
            fr"= {pretty_number(eta)}\,\%"
        ),
        sources=["2017_JEPE-10-335"],
    )
