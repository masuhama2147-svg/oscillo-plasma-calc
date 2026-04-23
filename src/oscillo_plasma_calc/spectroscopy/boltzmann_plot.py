"""Boltzmann-plot excitation temperature Te from multi-line intensities.

Implements the identical formula used in `励起温度計算シート ver.2.xlsx`:

  For each line i (with intensity I_i > 0):
      x_i = E_u,i − E_l,i                       [eV]   (xlsx convention K = C − D)
      y_i = ln[ I_i / (g_i · A_i · ν_i) ]       [-]
        where ν_i = c / λ_i

  Least-squares slope over n used lines:
      m = (n·Σxy − Σx·Σy) / (n·Σxx − (Σx)^2)

  Excitation temperature:
      Te = −1 / (k_B · m)            with k_B = 8.617333e−5 eV/K

A line with I_i = 0 is excluded (same convention as the xlsx).

References
----------
* Nomura lab 2006_JJAP-45-8864 (two-line Boltzmann method)
* Nomura lab 2009_JAP-106-113302 (spatial resolution of Te)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable

from ..config.constants import C_LIGHT
from ..report.trace import TraceResult
from ..report.ui_format import pretty_number
from .lines import SpectralLine, get_lines


K_B_eV_per_K = 8.61733363326e-5   # Boltzmann constant in eV/K (xlsx value)


@dataclass
class BoltzmannPlotResult:
    element: str
    Te_K: float
    slope: float                            # dimensionless (1/eV)
    n_used: int
    xs: list[float] = field(default_factory=list)
    ys: list[float] = field(default_factory=list)
    line_labels: list[str] = field(default_factory=list)
    excluded: list[str] = field(default_factory=list)
    r_squared: float = float("nan")        # LTE linearity indicator (0-1)

    @property
    def Te_eV(self) -> float:
        return self.Te_K * K_B_eV_per_K

    @property
    def lte_quality_label(self) -> str:
        """Verdict per 2026-04-23 lab meeting LTE discussion."""
        if not (self.n_used >= 3) or self.r_squared != self.r_squared:
            return "指標不足 (n<3)"
        if self.r_squared >= 0.95:
            return "LTE 直線性 良好"
        if self.r_squared >= 0.85:
            return "LTE 直線性 やや弱い"
        return "LTE 非成立の疑い"


def _line_xy(line: SpectralLine, intensity: float) -> tuple[float, float]:
    nu = C_LIGHT / (line.wavelength_nm * 1e-9)
    x = line.dE_eV                          # xlsx: K = C − D
    y = math.log(intensity / (line.g_upper * line.A_Einstein * nu))
    return x, y


def excitation_temperature(element: str,
                           intensities: dict[str, float],
                           lines: Iterable[SpectralLine] | None = None,
                           ) -> tuple[BoltzmannPlotResult, TraceResult]:
    """Fit Te via Boltzmann plot.

    Parameters
    ----------
    element : e.g. "H" / "O" / "W" / "Al" / "Cu"
    intensities : mapping from line label → measured intensity (a.u.).
                  Labels missing from the map or mapped to 0 are treated as
                  unused (same behaviour as the xlsx).
    lines : optional override of the line list. Defaults to LINE_DATABASE[element].
    """
    line_list = list(lines) if lines is not None else list(get_lines(element))
    xs, ys, used_labels, excluded = [], [], [], []
    for ln in line_list:
        I = float(intensities.get(ln.label, 0.0))
        if I <= 0:
            excluded.append(ln.label)
            continue
        x, y = _line_xy(ln, I)
        xs.append(x); ys.append(y); used_labels.append(ln.label)

    n = len(xs)
    if n < 2:
        bp = BoltzmannPlotResult(element=element, Te_K=float("nan"),
                                 slope=float("nan"), n_used=n,
                                 xs=xs, ys=ys,
                                 line_labels=used_labels, excluded=excluded)
        tr = TraceResult(
            name=f"Excitation temperature Te ({element})",
            value=float("nan"), unit="K",
            equation_latex=r"T_e = -\dfrac{1}{k_B\,m}",
            substitution_latex="",
            steps=[f"used lines n = {n} (need ≥ 2)"],
            sources=["2006_JJAP-45-8864", "2009_JAP-106-113302"],
        )
        return bp, tr

    Sx = sum(xs); Sy = sum(ys)
    Sxx = sum(x * x for x in xs)
    Syy = sum(y * y for y in ys)
    Sxy = sum(x * y for x, y in zip(xs, ys))
    denom = n * Sxx - Sx * Sx
    if denom == 0:
        m = float("nan")
    else:
        m = (n * Sxy - Sx * Sy) / denom
    Te_K = -1.0 / (K_B_eV_per_K * m) if m != 0 else float("inf")

    # R^2 — LTE linearity indicator (per 2026-04-23 lab meeting)
    r_squared = float("nan")
    num_r = n * Sxy - Sx * Sy
    den_r2 = (n * Sxx - Sx * Sx) * (n * Syy - Sy * Sy)
    if den_r2 > 0:
        r_squared = float((num_r * num_r) / den_r2)

    steps = [f"使用した発光線: {used_labels}",
             f"除外（I=0）: {excluded}" if excluded else "除外: なし",
             f"n = {n}",
             f"Σx = {Sx:.6g}",
             f"Σy = {Sy:.6g}",
             f"Σxx = {Sxx:.6g}",
             f"Σxy = {Sxy:.6g}",
             f"slope m = {m:.6g}  (1/eV)",
             f"R² = {r_squared:.4f}（LTE 直線性指標）"]

    eq = (r"y_i = \ln\!\left(\dfrac{I_i}{g_i A_i \nu_i}\right) = "
          r"-\dfrac{x_i}{k_B T_e} + C,\qquad "
          r"x_i = E_{u,i} - E_{l,i}")
    sub = (r"m = \dfrac{n\sum xy - \sum x\,\sum y}"
           r"{n\sum x^2 - (\sum x)^2} = "
           fr"{pretty_number(m)}\,\text{{eV}}^{{-1}};\quad "
           fr"T_e = -\dfrac{{1}}{{k_B\,m}} = {pretty_number(Te_K)}\,\text{{K}}")

    tr = TraceResult(
        name=f"Excitation temperature Te ({element})",
        value=Te_K, unit="K",
        equation_latex=eq,
        substitution_latex=sub,
        steps=steps,
        sources=["2006_JJAP-45-8864", "2009_JAP-106-113302",
                 "励起温度計算シート ver.2.xlsx"],
        extra={"xs": xs, "ys": ys,
               "labels": used_labels, "slope": m, "n_used": n},
    )
    bp = BoltzmannPlotResult(element=element, Te_K=Te_K, slope=m,
                             n_used=n, xs=xs, ys=ys,
                             line_labels=used_labels, excluded=excluded,
                             r_squared=r_squared)
    tr.extra["r_squared"] = r_squared
    tr.extra["lte_quality"] = bp.lte_quality_label
    return bp, tr
