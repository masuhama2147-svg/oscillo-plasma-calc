"""Lissajous / Manley method: P̄ = f · ∮ V dq (DBD-style power).

When an electrode is coupled via a blocking dielectric (monitor capacitor Cm),
the charge q(t) is obtained from the voltage across Cm. Here we synthesize
q(t) = ∫ I(t) dt from the measured discharge current, then compute the closed
V-q loop area times pulse repetition frequency.

Reference: DBD power measurement principle (Manley 1943); applied in Nomura-lab
nanosecond-pulse studies (2013_CAP-13-1050 context).
"""
from __future__ import annotations

import numpy as np
from scipy.integrate import cumulative_trapezoid

from ..report.trace import TraceResult
from ..report.ui_format import format_si, pretty_number


def _loop_area(v: np.ndarray, q: np.ndarray) -> float:
    """Shoelace formula for the signed area of a V-q closed loop."""
    return 0.5 * float(np.abs(np.sum(v * np.roll(q, -1) - np.roll(v, -1) * q)))


def lissajous_power(t: np.ndarray, v: np.ndarray, i: np.ndarray,
                    pulse_rep_freq_hz: float | None = None) -> TraceResult:
    t = np.asarray(t, float); v = np.asarray(v, float); i = np.asarray(i, float)
    q = cumulative_trapezoid(i, t, initial=0.0)   # C
    area = _loop_area(v, q)                       # V·C = J per cycle
    if pulse_rep_freq_hz is None:
        duration = float(t[-1] - t[0])
        pulse_rep_freq_hz = 1.0 / duration if duration > 0 else float("nan")
    P = area * pulse_rep_freq_hz
    return TraceResult(
        name="Lissajous (V–q) mean power",
        value=P, unit="W",
        equation_latex=r"\bar{P} = f \oint V\,dq",
        substitution_latex=(
            fr"\bar{{P}} = {format_si(pulse_rep_freq_hz, 'Hz')} "
            fr"\times {pretty_number(area)}\,\text{{J/cycle}} "
            fr"= {format_si(P, 'W')}"
        ),
        steps=[
            "q(t) = ∫ I(t) dt  (cumulative trapezoid)",
            "loop area ≡ energy per cycle (shoelace on V–q plane)",
            f"assumed f = {pulse_rep_freq_hz:.4g} Hz",
        ],
        sources=["Manley 1943", "2013_CAP-13-1050"],
        extra={"q": q, "loop_area_J": area, "f_hz": pulse_rep_freq_hz},
    )
