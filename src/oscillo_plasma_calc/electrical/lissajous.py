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
    duration = float(t[-1] - t[0])
    window_freq = 1.0 / duration if duration > 0 else float("nan")
    # Phase 0.3: time-base separation. Default to user PRF; fall back to window.
    if pulse_rep_freq_hz is None:
        pulse_rep_freq_hz = window_freq
        time_basis = "window"
    else:
        time_basis = "PRF"
    P = area * pulse_rep_freq_hz
    basis_note = (
        f"PRF = {pulse_rep_freq_hz:.4g} Hz (user input)"
        if time_basis == "PRF"
        else f"window-derived f = {window_freq:.4g} Hz (1 / T_window)"
    )
    return TraceResult(
        name=f"Lissajous mean power ({time_basis} basis)",
        value=P, unit="W",
        equation_latex=r"\bar{P}_\mathrm{Liss} = f \oint V\,dq",
        substitution_latex=(
            fr"\bar{{P}}_\mathrm{{Liss}} = {format_si(pulse_rep_freq_hz, 'Hz')} "
            fr"\times {pretty_number(area)}\,\text{{J/cycle}} "
            fr"= {format_si(P, 'W')}"
        ),
        steps=[
            "q(t) = ∫ I(t) dt  (cumulative trapezoid)",
            "loop area ≡ energy per cycle (shoelace on V–q plane)",
            f"time basis: {basis_note}",
            ("⚠ This is the Lissajous P̄ at the chosen frequency. "
             "Different from window-average P̄ = E / T_window. "
             "If both are shown, compare carefully — they answer different questions."),
        ],
        sources=["Manley 1943", "2013_CAP-13-1050"],
        extra={
            "q": q, "loop_area_J": area, "f_hz": pulse_rep_freq_hz,
            "time_basis": time_basis,
            "window_freq_hz": window_freq,
        },
    )
