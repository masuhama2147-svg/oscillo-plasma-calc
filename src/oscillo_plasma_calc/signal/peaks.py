"""Peak-to-peak, rise time, and slew-rate detectors.

Reference: Nomura lab 2013_CAP-13-1050 (ns-pulse breakdown characterization).
"""
from __future__ import annotations

import numpy as np
from ..report.trace import TraceResult
from ..report.ui_format import format_si, pretty_number


def _pp(x: np.ndarray) -> tuple[float, float, float]:
    xmax = float(np.max(x)); xmin = float(np.min(x))
    return xmax, xmin, xmax - xmin


def detect_vpp(v: np.ndarray) -> TraceResult:
    vmax, vmin, vpp = _pp(v)
    return TraceResult(
        name="Peak-to-peak voltage Vpp",
        value=vpp, unit="V",
        equation_latex=r"V_{pp} = V_{\max} - V_{\min}",
        substitution_latex=(
            fr"V_{{pp}} = {format_si(vmax, 'V')} - ({format_si(vmin, 'V')}) "
            fr"= {format_si(vpp, 'V')}"
        ),
        sources=["2013_CAP-13-1050"],
        extra={"v_max": vmax, "v_min": vmin},
    )


def detect_ipp(i: np.ndarray) -> TraceResult:
    imax, imin, ipp = _pp(i)
    return TraceResult(
        name="Peak-to-peak current Ipp",
        value=ipp, unit="A",
        equation_latex=r"I_{pp} = I_{\max} - I_{\min}",
        substitution_latex=(
            fr"I_{{pp}} = {format_si(imax, 'A')} - ({format_si(imin, 'A')}) "
            fr"= {format_si(ipp, 'A')}"
        ),
        sources=["2013_CAP-13-1050"],
        extra={"i_max": imax, "i_min": imin},
    )


def rise_time(t: np.ndarray, x: np.ndarray,
              lo: float = 0.1, hi: float = 0.9) -> TraceResult:
    """10 %→90 % rise time across the largest excursion."""
    xmax = float(np.max(x)); xmin = float(np.min(x))
    span = xmax - xmin
    if span <= 0:
        return TraceResult(name="Rise time",
                           value=float("nan"), unit="s",
                           equation_latex=r"t_{r} = t(|x|=0.9) - t(|x|=0.1)")
    x_lo = xmin + lo * span
    x_hi = xmin + hi * span
    try:
        idx_lo = int(np.argmax(x >= x_lo))
        idx_hi = int(np.argmax(x >= x_hi))
        tr = float(t[idx_hi] - t[idx_lo])
    except (ValueError, IndexError):
        tr = float("nan")
    return TraceResult(
        name=f"Rise time t_r ({int(lo*100)}%→{int(hi*100)}%)",
        value=tr, unit="s",
        equation_latex=fr"t_r = t(x={hi}\,x_{{\max}}) - t(x={lo}\,x_{{\max}})",
        substitution_latex=fr"t_r = {format_si(tr, 's')}",
        sources=["2013_CAP-13-1050"],
    )


def slew_rate(t: np.ndarray, x: np.ndarray, label: str = "V") -> TraceResult:
    """dV/dt (or dI/dt) via central differences — report the peak absolute slope."""
    dt = np.gradient(t)
    dxdt = np.gradient(x) / dt
    sr = float(np.max(np.abs(dxdt)))
    sym = "V" if label.upper().startswith("V") else "I"
    unit = "V/s" if sym == "V" else "A/s"
    return TraceResult(
        name=f"Peak slew rate d{sym}/dt",
        value=sr, unit=unit,
        equation_latex=fr"\left.\frac{{d{sym}}}{{dt}}\right|_{{\max}}"
                       fr"= \max_k \left|\frac{{{sym}_{{k+1}}-{sym}_{{k-1}}}}{{2\Delta t}}\right|",
        substitution_latex=(
            fr"\left.\frac{{d{sym}}}{{dt}}\right|_{{\max}} = "
            fr"{pretty_number(sr)}\,\text{{{unit}}}"
        ),
        sources=["2013_CAP-13-1050"],
    )
