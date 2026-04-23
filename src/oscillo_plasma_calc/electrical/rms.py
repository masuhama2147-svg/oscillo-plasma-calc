"""RMS voltage and current — standard AC circuit theory."""
from __future__ import annotations

import numpy as np
from scipy.integrate import trapezoid

from ..report.trace import TraceResult
from ..report.ui_format import format_si


def _rms_from_signal(t: np.ndarray, x: np.ndarray) -> float:
    T = float(t[-1] - t[0])
    if T <= 0:
        return float(np.sqrt(np.mean(x**2)))
    return float(np.sqrt(trapezoid(x**2, t) / T))


def v_rms(t: np.ndarray, v: np.ndarray) -> TraceResult:
    val = _rms_from_signal(np.asarray(t, float), np.asarray(v, float))
    return TraceResult(
        name="Voltage RMS Vrms",
        value=val, unit="V",
        equation_latex=r"V_\mathrm{rms} = \sqrt{\tfrac{1}{T}\int_0^T V(t)^2\,dt}",
        substitution_latex=fr"V_\mathrm{{rms}} = {format_si(val, 'V')}",
        sources=["classical AC circuit theory"],
    )


def i_rms(t: np.ndarray, i: np.ndarray) -> TraceResult:
    val = _rms_from_signal(np.asarray(t, float), np.asarray(i, float))
    return TraceResult(
        name="Current RMS Irms",
        value=val, unit="A",
        equation_latex=r"I_\mathrm{rms} = \sqrt{\tfrac{1}{T}\int_0^T I(t)^2\,dt}",
        substitution_latex=fr"I_\mathrm{{rms}} = {format_si(val, 'A')}",
        sources=["classical AC circuit theory"],
    )
