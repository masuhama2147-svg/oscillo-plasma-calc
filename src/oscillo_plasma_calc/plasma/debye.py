"""Debye length and plasma frequency."""
from __future__ import annotations

import math
from ..config.constants import EPSILON_0, K_B, E_CHARGE, M_E
from ..report.trace import TraceResult
from ..report.ui_format import format_si, pretty_number


def debye_length(Te_eV: float, ne_m3: float) -> TraceResult:
    Te_K = Te_eV * E_CHARGE / K_B
    lam = math.sqrt(EPSILON_0 * K_B * Te_K / (ne_m3 * E_CHARGE ** 2))
    return TraceResult(
        name="Debye length λ_D",
        value=lam, unit="m",
        equation_latex=r"\lambda_D = \sqrt{\varepsilon_0 k_B T_e/(n_e e^2)}",
        substitution_latex=(
            fr"\lambda_D = \sqrt{{\varepsilon_0\,k_B\,T_e/(n_e e^2)}} "
            fr"\;\Big|_{{T_e={pretty_number(Te_K)}\,\text{{K}},\;"
            fr"n_e={pretty_number(ne_m3)}\,\text{{m}}^{{-3}}}} "
            fr"= {format_si(lam, 'm')}"
        ),
        steps=[f"Te = {Te_eV:.4g} eV → {Te_K:.4g} K"],
        sources=["classical plasma physics"],
    )


def plasma_frequency(ne_m3: float) -> TraceResult:
    fp = (1.0 / (2.0 * math.pi)) * math.sqrt(
        ne_m3 * E_CHARGE ** 2 / (M_E * EPSILON_0)
    )
    return TraceResult(
        name="Electron plasma frequency f_p",
        value=fp, unit="Hz",
        equation_latex=r"f_p = \frac{1}{2\pi}\sqrt{n_e e^2/(m_e \varepsilon_0)}",
        substitution_latex=fr"f_p = {format_si(fp, 'Hz')}",
        sources=["2008_APEX-1-046002"],
    )
