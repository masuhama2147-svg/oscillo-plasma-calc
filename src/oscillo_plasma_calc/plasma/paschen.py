"""Paschen breakdown voltage for gas gaps.

  V_b = B · p · d / [ ln(A · p · d) − ln(ln(1 + 1/γ)) ]

Reference: 2013_CAP-13-1050 (ns-pulse breakdown characterization in liquids).
"""
from __future__ import annotations

import math
from ..report.trace import TraceResult
from ..report.ui_format import format_si, pretty_number


def paschen_breakdown_voltage(p_Pa: float, d_m: float,
                              A: float = 112.5, B: float = 2737.5,
                              gamma: float = 0.01) -> TraceResult:
    pd = p_Pa * d_m
    try:
        denom = math.log(A * pd) - math.log(math.log(1.0 + 1.0 / gamma))
        Vb = (B * pd) / denom
    except (ValueError, ZeroDivisionError):
        Vb = float("nan")
    return TraceResult(
        name="Paschen breakdown voltage V_b",
        value=Vb, unit="V",
        equation_latex=(
            r"V_b = \frac{B\,p\,d}{\ln(A\,p\,d) - \ln\!\ln(1+1/\gamma)}"
        ),
        substitution_latex=(
            fr"V_b = \frac{{{pretty_number(B)}\,\text{{V/(Pa·m)}}"
            fr"\;\times\;{pretty_number(pd)}\,\text{{Pa·m}}}}"
            fr"{{\ln({pretty_number(A*pd)}) - \ln\ln(1+1/{pretty_number(gamma)})}} "
            fr"= {format_si(Vb, 'V')}"
        ),
        steps=[f"pd = {pd:.4g} Pa·m", f"A={A:.4g}, B={B:.4g}, γ={gamma:.3g}"],
        sources=["2013_CAP-13-1050"],
    )
