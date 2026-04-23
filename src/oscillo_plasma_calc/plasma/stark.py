"""Electron density from Stark broadening of H_α / H_β.

  n_e = α(T_e) · (Δλ_{1/2})^{3/2}                         [m^-3, nm input]

Reference: Nomura lab 2009_POP-16-033503 (H_α Stark profile method).

The Stark coefficient α depends weakly on Te; we expose it as a keyword so
callers can supply the value fitted for their pressure range. A typical choice
for H_α at atmospheric-pressure water-plasma is α ≈ 1.0e23 m^-3 / nm^{3/2}.
"""
from __future__ import annotations

from ..report.trace import TraceResult
from ..report.ui_format import pretty_number


def electron_density_stark(
    fwhm_nm: float,
    alpha: float = 1.0e23,   # m^-3 · nm^(-3/2)
    line: str = "H_alpha",
) -> TraceResult:
    n_e = alpha * fwhm_nm ** 1.5
    return TraceResult(
        name=f"Electron density n_e (Stark, {line})",
        value=n_e, unit="m^-3",
        equation_latex=r"n_e = \alpha(T_e)\,(\Delta\lambda_{1/2})^{3/2}",
        substitution_latex=(
            fr"n_e = {pretty_number(alpha)}\,\text{{m}}^{{-3}}\text{{nm}}^{{-3/2}} "
            fr"\times ({pretty_number(fwhm_nm)}\,\text{{nm}})^{{3/2}} "
            fr"= {pretty_number(n_e)}\,\text{{m}}^{{-3}}"
        ),
        steps=[
            f"line = {line}",
            f"Stark coefficient α = {alpha:.4g} m^-3·nm^(-3/2)",
        ],
        sources=["2009_POP-16-033503"],
    )
