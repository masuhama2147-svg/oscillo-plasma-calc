"""Instantaneous electrical power P(t) = V(t)·I(t).

Reference: 2006_JJAP-45-8864, 2011_PSST-20-034016 (Nomura lab waveform analysis).
"""
from __future__ import annotations

import numpy as np
from ..report.trace import TraceResult
from ..report.ui_format import format_si


def instantaneous_power(v: np.ndarray, i: np.ndarray) -> TraceResult:
    v = np.asarray(v, dtype=float); i = np.asarray(i, dtype=float)
    p = v * i
    return TraceResult(
        name="Instantaneous power P(t)",
        value=p, unit="W",
        equation_latex=r"P(t) = V(t)\cdot I(t)",
        substitution_latex=r"P_k = V_k \cdot I_k \quad (k=0,\dots,N-1)",
        steps=[f"N = {v.size} samples"],
        sources=["2006_JJAP-45-8864", "2011_PSST-20-034016"],
    )


def peak_power(v: np.ndarray, i: np.ndarray) -> TraceResult:
    p = np.asarray(v, dtype=float) * np.asarray(i, dtype=float)
    pk_idx = int(np.argmax(np.abs(p)))
    pk = float(p[pk_idx])
    return TraceResult(
        name="Peak instantaneous power |P|_max",
        value=pk, unit="W",
        equation_latex=r"P_\mathrm{peak} = \max_k |V_k I_k|",
        substitution_latex=fr"P_\mathrm{{peak}} = {format_si(pk, 'W')}",
        sources=["2006_JJAP-45-8864"],
        extra={"peak_index": pk_idx},
    )
