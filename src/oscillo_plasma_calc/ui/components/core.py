"""Reusable UI/data helpers for researcher-oriented Shiny screens.

The functions here intentionally avoid importing Shiny.  They prepare small,
testable data structures that `ui.app` can render as cards, tables and export
rows without changing the calculation layer.
"""
from __future__ import annotations

import csv
import io
import math
from dataclasses import dataclass
from typing import Iterable

import numpy as np
import plotly.graph_objects as go

from oscillo_plasma_calc.report.trace import TraceResult


PAPER_TEMPLATE = "plotly_white"
SCREEN_TEMPLATE = "plotly"
IMPORTANT_KEYS = {
    "vpp", "ipp", "rise_time", "peak_power", "energy", "mean_power",
    "effective_average_power", "budget_margin", "g_value", "efficiency",
    "sei", "energy_cost", "chi_co2", "eta_se", "asf", "excitation_temp",
    "boltzmann_two_line", "stark", "e_over_n", "tv_rot_ratio",
}
PAPER_CANDIDATE_KEYS = {
    "vpp", "ipp", "energy", "mean_power", "lissajous",
    "effective_average_power", "g_value", "efficiency", "sei",
    "energy_cost", "chi_co2", "eta_se", "asf", "excitation_temp",
}


@dataclass(frozen=True)
class KpiRow:
    group: str
    quantity: str
    value: str
    unit: str
    status: str
    source: str
    equation_key: str


def display_value(tr: TraceResult, sig: int = 4) -> str:
    """Compact scalar value for UI tables and CSV export."""
    value = tr.scalar()
    if value is None:
        return "array"
    if math.isnan(value):
        return "nan"
    if math.isinf(value):
        return "inf" if value > 0 else "-inf"
    mag = abs(value)
    if value == 0 or 1e-3 <= mag < 1e4:
        return f"{value:.{sig}g}"
    mantissa, exponent = f"{value:.{sig - 1}e}".split("e")
    return f"{mantissa}e{int(exponent)}"


def status_label(tr: TraceResult) -> str:
    """Return the anomaly level as a stable export/UI token."""
    if tr.anomaly is None:
        return "not_checked"
    return str(tr.anomaly.level)


def trace_rows(traces: Iterable[TraceResult]) -> list[KpiRow]:
    rows: list[KpiRow] = []
    for tr in traces:
        if tr.scalar() is None:
            continue
        rows.append(KpiRow(
            group=getattr(tr, "category", "other"),
            quantity=tr.name,
            value=display_value(tr),
            unit=tr.unit,
            status=status_label(tr),
            source=", ".join(tr.sources),
            equation_key=tr.explanation_key or "",
        ))
    return rows


def export_trace_csv(traces: Iterable[TraceResult]) -> str:
    """Build CSV for calculated quantities, not raw waveform samples."""
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["quantity", "value", "unit", "status", "source", "equation_key"])
    for row in trace_rows(traces):
        writer.writerow([
            row.quantity, row.value, row.unit, row.status, row.source,
            row.equation_key,
        ])
    return out.getvalue()


def important_traces(traces: Iterable[TraceResult]) -> list[TraceResult]:
    """Sorted list of warning-critical and researcher-facing KPIs."""
    severity = {"error": 0, "warning": 1, "notice": 2, "ok": 3, "not_checked": 4}

    def rank(tr: TraceResult) -> tuple[int, int, str]:
        key = tr.explanation_key or ""
        lvl = status_label(tr)
        priority = 0 if key in IMPORTANT_KEYS else 1
        return (severity.get(lvl, 4), priority, tr.name)

    selected = [
        tr for tr in traces
        if tr.scalar() is not None
        and ((tr.explanation_key or "") in IMPORTANT_KEYS
             or status_label(tr) in {"warning", "error", "notice"})
    ]
    return sorted(selected, key=rank)


def paper_candidate_traces(traces: Iterable[TraceResult]) -> list[TraceResult]:
    return [
        tr for tr in traces
        if tr.scalar() is not None and (tr.explanation_key or "") in PAPER_CANDIDATE_KEYS
    ]


def plotly_mode_template(mode: str) -> str:
    return PAPER_TEMPLATE if mode == "paper" else SCREEN_TEMPLATE


def apply_research_plot_layout(fig: go.Figure, mode: str = "screen") -> go.Figure:
    """Apply a consistent screen/paper visual style to Plotly figures."""
    template = plotly_mode_template(mode)
    font_size = 13 if mode == "paper" else 12
    fig.update_layout(
        template=template,
        font=dict(size=font_size, family="Arial"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1),
        margin=dict(l=70, r=70, t=70, b=60),
    )
    fig.update_xaxes(showline=True, linewidth=1, linecolor="#333", mirror=True)
    fig.update_yaxes(showline=True, linewidth=1, linecolor="#333", mirror=True)
    return fig


def waveform_annotations(t_s: np.ndarray, v: np.ndarray, i: np.ndarray) -> dict[str, float]:
    """Return positions used to annotate V/I peaks, rise time and zero crossing."""
    t_s = np.asarray(t_s, dtype=float)
    v = np.asarray(v, dtype=float)
    i = np.asarray(i, dtype=float)
    if t_s.size == 0:
        return {}
    idx_vmax = int(np.nanargmax(v))
    idx_vmin = int(np.nanargmin(v))
    idx_imax = int(np.nanargmax(np.abs(i)))
    vmax = float(v[idx_vmax])
    vmin = float(v[idx_vmin])
    v10 = vmin + 0.1 * (vmax - vmin)
    v90 = vmin + 0.9 * (vmax - vmin)
    above10 = np.where(v >= v10)[0]
    above90 = np.where(v >= v90)[0]
    idx10 = int(above10[0]) if above10.size else idx_vmax
    idx90 = int(above90[0]) if above90.size else idx_vmax
    sign_change = np.where(np.diff(np.signbit(v)))[0]
    idx_zero = int(sign_change[0]) if sign_change.size else idx_vmax
    return {
        "t_vmax_us": float(t_s[idx_vmax] * 1e6),
        "vmax": vmax,
        "t_vmin_us": float(t_s[idx_vmin] * 1e6),
        "vmin": vmin,
        "t_imax_us": float(t_s[idx_imax] * 1e6),
        "imax": float(i[idx_imax]),
        "t10_us": float(t_s[idx10] * 1e6),
        "v10": float(v[idx10]),
        "t90_us": float(t_s[idx90] * 1e6),
        "v90": float(v[idx90]),
        "t_zero_us": float(t_s[idx_zero] * 1e6),
    }


def anomaly_markdown(traces: Iterable[TraceResult]) -> str:
    alerts = [
        tr for tr in traces
        if tr.scalar() is not None and status_label(tr) in {"notice", "warning", "error"}
    ]
    if not alerts:
        return "## 異常値・注意値\n\n- なし\n\n"
    lines = ["## 異常値・注意値", ""]
    for tr in alerts:
        anomaly = tr.anomaly
        lines.append(f"- **{tr.name}**: {display_value(tr)} {tr.unit} "
                     f"({anomaly.level}) — {anomaly.message}")
    lines.append("")
    return "\n".join(lines)


def figure_guidance_markdown() -> str:
    return """## 図表の読み方

- Waveform: V/I のピーク、10–90% 立ち上がり、ゼロクロスを確認し、放電開始とプローブ帯域を点検する。
- Electrical: P(t) と累積 E(t) を見比べ、単発パルスの鋭さと観測窓平均の妥当性を確認する。
- Lissajous: V-q ループ面積を平均電力の独立チェックとして使う。
- FFT: 支配周波数、2f/3f 高調波、Nyquist 線を確認し、駆動源と非線形応答を切り分ける。
- Boltzmann plot: R2、採用線数、除外線を確認し、LTE 直線性が弱い場合は線選択と感度補正を見直す。

"""
