"""Energy absorbed by the discharge: E = ∫ V(t)·I(t) dt (trapezoid rule).

Reference: 2008_APEX-1-046002 (RF vs microwave power coupling comparison).
"""
from __future__ import annotations

import numpy as np
from scipy.integrate import cumulative_trapezoid, trapezoid

from ..report.trace import TraceResult
from ..report.ui_format import format_si


def absorbed_energy(t: np.ndarray, v: np.ndarray, i: np.ndarray) -> TraceResult:
    t = np.asarray(t, dtype=float)
    p = np.asarray(v, dtype=float) * np.asarray(i, dtype=float)
    E = float(trapezoid(p, t))
    E_cum = cumulative_trapezoid(p, t, initial=0.0)
    return TraceResult(
        name="Absorbed energy E (∫ V·I dt)",
        value=E, unit="J",
        equation_latex=r"E = \int_{t_0}^{t_N} V(t)\,I(t)\,dt",
        substitution_latex=(
            r"E \approx \sum_{k=0}^{N-2} \frac{(P_k+P_{k+1})}{2}(t_{k+1}-t_k)"
            fr" = {format_si(E, 'J')}"
        ),
        steps=[
            "method: composite trapezoidal rule",
            f"duration T = {t[-1]-t[0]:.4g} s",
            f"N = {t.size} samples",
        ],
        sources=["2008_APEX-1-046002"],
        extra={"E_cumulative": E_cum},
    )


def mean_power(t: np.ndarray, v: np.ndarray, i: np.ndarray) -> TraceResult:
    e = absorbed_energy(t, v, i)
    duration = float(t[-1] - t[0])
    P_avg = e.value / duration if duration > 0 else float("nan")
    return TraceResult(
        name="Time-average power P̄",
        value=P_avg, unit="W",
        equation_latex=r"\bar{P} = \frac{1}{T}\int_0^T V(t)\,I(t)\,dt",
        substitution_latex=(
            fr"\bar{{P}} = \frac{{{format_si(e.value, 'J')}}}"
            fr"{{{format_si(duration, 's')}}} = {format_si(P_avg, 'W')}"
        ),
        steps=[f"E = {e.value:.4g} J", f"T = {duration:.4g} s"],
        sources=["2008_APEX-1-046002", "2011_PSST-20-034016"],
    )
