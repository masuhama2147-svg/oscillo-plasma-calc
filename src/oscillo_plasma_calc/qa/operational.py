"""Device-wide operational budget checks (user requirement 2026-04-23).

実装の思想: 研究室では 装置全体 1 kW 以下で運用する慣例があり、これを
波形解析から自動監視する。
"""
from __future__ import annotations

from ..report.trace import TraceResult
from ..report.ui_format import format_si, pretty_number
from .anomaly import AnomalyResult


DEFAULT_BUDGET_W = 1000.0


def device_power_budget(p_est_W: float,
                         budget_W: float = DEFAULT_BUDGET_W) -> TraceResult:
    """Check P_est against the facility budget W_budget.

    Returns TraceResult with an attached AnomalyResult whose level reflects:
      ok       : P_est < 0.7 · budget       （余裕 > 30 %）
      notice   : 0.7 ≤ P_est/budget < 0.9   （余裕 10-30 %）
      warning  : 0.9 ≤ P_est/budget < 1.0   （余裕 < 10 %）
      error    : P_est ≥ budget             （超過、運用停止検討）
    """
    if budget_W <= 0:
        return TraceResult(
            name="Device-wide power budget margin",
            value=float("nan"), unit="%",
            equation_latex=r"M = (W_\mathrm{budget} - P_\mathrm{est})/W_\mathrm{budget}",
        )
    margin_frac = (budget_W - p_est_W) / budget_W
    margin_pct = margin_frac * 100.0

    # Determine level
    ratio = p_est_W / budget_W
    if ratio >= 1.0:
        level, msg = "error", (
            f"推定平均 {p_est_W:.1f} W が予算 {budget_W:.0f} W を超過。"
            "運用停止 or 駆動条件見直しを推奨")
        causes = ["PRF / デューティ比 が設計想定より大", "駆動パルス電圧が過大"]
    elif ratio >= 0.9:
        level, msg = "warning", (
            f"余裕 {margin_pct:.1f} %（10 % 未満）。瞬時ピーク超過の恐れ")
        causes = ["PRF を下げる / パルス幅を短くする"]
    elif ratio >= 0.7:
        level, msg = "notice", f"余裕 {margin_pct:.1f} %（10-30 %）"
        causes = []
    else:
        level, msg = "ok", f"余裕 {margin_pct:.1f} %（30 % 以上、健全）"
        causes = []

    anomaly = AnomalyResult(
        level=level, message=msg,
        causes=causes,
        references=["lab meeting 2026-04-23", "社内運用基準 1 kW ライン"],
        range_low=0, range_high=budget_W, unit="W",
    )

    tr = TraceResult(
        name="Device-wide power budget margin",
        value=margin_pct, unit="%",
        equation_latex=(
            r"M = \dfrac{W_\mathrm{budget} - P_\mathrm{est}}{W_\mathrm{budget}}"
            r"\times 100\%"
        ),
        substitution_latex=(
            fr"M = \dfrac{{{format_si(budget_W, 'W')} - {format_si(p_est_W, 'W')}}}"
            fr"{{{format_si(budget_W, 'W')}}}\times 100\% "
            fr"= {pretty_number(margin_pct)}\,\%"
        ),
        steps=[f"装置予算 W_budget = {budget_W:.0f} W",
               f"推定平均 P_est = {p_est_W:.1f} W",
               f"比率 P_est/W_budget = {ratio*100:.1f} %"],
        sources=["lab meeting 2026-04-23"],
    )
    tr.anomaly = anomaly
    return tr


def heat_dissipation_requirement(p_mean_W: float,
                                  p_chem_W: float = 0.0) -> TraceResult:
    """Q_cool = P̄_plasma - P̄_chem. Heat to be removed by cooling."""
    q = p_mean_W - p_chem_W
    return TraceResult(
        name="Heat dissipation requirement Q_cool",
        value=q, unit="W",
        equation_latex=r"Q_\mathrm{cool} = \bar{P}_\mathrm{plasma} - \bar{P}_\mathrm{chem}",
        substitution_latex=(
            fr"Q_\mathrm{{cool}} = {format_si(p_mean_W, 'W')} - "
            fr"{format_si(p_chem_W, 'W')} = {format_si(q, 'W')}"
        ),
        steps=["化学エネルギーに変換されず熱になる分の目安",
               "水冷 or 強制空冷の熱交換容量に反映"],
        sources=["plasma reactor thermal management"],
    )


def device_efficiency(p_mean_W: float, w_socket_W: float) -> TraceResult:
    """η_device = P̄ / W_socket. Fraction of facility power ending up in plasma."""
    if w_socket_W <= 0:
        return TraceResult(
            name="Device-to-plasma efficiency η_dev",
            value=float("nan"), unit="%",
            equation_latex=r"\eta_\mathrm{dev} = \bar{P}/W_\mathrm{socket}",
        )
    eta = p_mean_W / w_socket_W * 100.0
    return TraceResult(
        name="Device-to-plasma efficiency η_dev",
        value=eta, unit="%",
        equation_latex=r"\eta_\mathrm{dev} = \dfrac{\bar{P}_\mathrm{plasma}}{W_\mathrm{socket}}\times 100\%",
        substitution_latex=(
            fr"\eta_\mathrm{{dev}} = \dfrac{{{format_si(p_mean_W, 'W')}}}"
            fr"{{{format_si(w_socket_W, 'W')}}}\times 100\% "
            fr"= {pretty_number(eta)}\,\%"
        ),
        steps=["会議議事録 2026-04-23: コンセント側比較指標",
               "70〜95 % が妥当レンジ（待機電力を除外後）"],
        sources=["lab meeting 2026-04-23"],
    )
