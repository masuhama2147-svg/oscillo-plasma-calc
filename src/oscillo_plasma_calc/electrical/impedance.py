"""Instantaneous impedance Z(t) = V(t)/I(t) with zero-crossing guard."""
from __future__ import annotations

import numpy as np
from ..report.trace import TraceResult


def instant_impedance(v: np.ndarray, i: np.ndarray,
                      i_threshold: float = 1e-3) -> TraceResult:
    v = np.asarray(v, float); i = np.asarray(i, float)
    z = np.where(np.abs(i) > i_threshold, v / np.where(i == 0, np.nan, i), np.nan)
    return TraceResult(
        name="Instantaneous impedance Z(t)",
        value=z, unit="Ω",
        equation_latex=r"Z(t) = V(t)/I(t)",
        substitution_latex=fr"Z_k = V_k / I_k \text{{ ; undefined when }} |I_k|<{i_threshold}\,\mathrm{{A}}",
        sources=["classical AC circuit theory"],
    )
