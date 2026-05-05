"""G1–G6 research-decision gate orchestration.

Gate flow (per ux_redesign_researcher_plan.md and 2026-04-23 lab meeting):

    G1 Data Valid       —— Upload tab passed validation
    G2 Energy Valid     —— bundle.energy is finite and physically plausible
    G3 Te Valid         —— BoltzmannPlotResult.is_te_reliable (R²≥0.85, n≥3)
    G4 Thermo Valid     —— NASA polynomial available for all needed species
    G5 Equilibrium Valid—— Gibbs minimization converged, element balance ok
    G6 Research Valid   —— G1-G5 all passed → ready for paper / report

Locked downstream gates show "blocker" text so the researcher knows
exactly *why* the next button is disabled.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class GateStatus:
    name: str           # "G1 Data Valid"
    passed: bool
    blocker: str        # empty when passed; otherwise a one-liner
    icon: str           # "✅" / "⚠️" / "⛔"
    severity: str       # "ok" / "provisional" / "locked"
    detail: str = ""    # extra context for tooltip / detail panel


def _gate_g1(validation) -> GateStatus:
    if validation is None:
        return GateStatus("G1 Data Valid", False,
                          "CSV / xlsx を読み込んでください",
                          "⛔", "locked")
    if validation.passed:
        n_warn = len(validation.warnings)
        msg = f"OK ({n_warn} warnings)" if n_warn else "OK"
        return GateStatus("G1 Data Valid", True, "", "✅", "ok", msg)
    blocker = validation.hard_errors[0].message if validation.hard_errors else "形式違反"
    return GateStatus("G1 Data Valid", False, blocker, "⛔", "locked")


def _gate_g2(bundle) -> GateStatus:
    if bundle is None:
        return GateStatus("G2 Energy Valid", False,
                          "G1 通過後に自動計算されます",
                          "⛔", "locked")
    e = bundle.energy.scalar() if bundle.energy is not None else None
    if e is None or not math.isfinite(e):
        return GateStatus("G2 Energy Valid", False,
                          "吸収エネルギーが nan/inf",
                          "⛔", "locked")
    if e <= 1e-5:                       # 10 μJ minimum
        return GateStatus("G2 Energy Valid", False,
                          f"E = {e*1e3:.2g} mJ < 0.01 mJ → 放電未点弧の疑い",
                          "⚠️", "provisional")
    return GateStatus("G2 Energy Valid", True, "", "✅", "ok",
                      f"E = {e*1e3:.3g} mJ")


def _gate_g3(spec_bp) -> GateStatus:
    if spec_bp is None:
        return GateStatus("G3 Te Valid", False,
                          "発光分光強度を入力して Te を計算してください",
                          "⛔", "locked")
    if not getattr(spec_bp, "is_te_reliable", False):
        warn = getattr(spec_bp, "reliability_warning", "Te 信頼性不足")
        return GateStatus("G3 Te Valid", False, warn, "⚠️", "provisional",
                          f"R²={getattr(spec_bp, 'r_squared', float('nan')):.3f}, "
                          f"n={getattr(spec_bp, 'n_used', 0)}")
    return GateStatus("G3 Te Valid", True, "", "✅", "ok",
                      f"Te={spec_bp.Te_K:.0f} K, R²={spec_bp.r_squared:.3f}")


def _gate_g4(thermo_state, g3: GateStatus) -> GateStatus:
    """Thermo DB validity. Requires G3 (Te in valid range)."""
    if not g3.passed:
        return GateStatus("G4 Thermo Valid", False,
                          f"先に G3 を通過 ({g3.blocker})",
                          "⛔", "locked")
    if thermo_state is None or not getattr(thermo_state, "all_species_in_range", True):
        return GateStatus("G4 Thermo Valid", False,
                          "NASA polynomial が species を温度範囲内にカバーしていない",
                          "⛔", "locked")
    return GateStatus("G4 Thermo Valid", True, "", "✅", "ok")


def _gate_g5(equilibrium_state, g4: GateStatus) -> GateStatus:
    if not g4.passed:
        return GateStatus("G5 Equilibrium Valid", False,
                          f"先に G4 を通過 ({g4.blocker})",
                          "⛔", "locked")
    if equilibrium_state is None:
        return GateStatus("G5 Equilibrium Valid", False,
                          "Equilibrium タブで計算してください",
                          "⛔", "locked")
    converged = getattr(equilibrium_state, "converged", False)
    err = getattr(equilibrium_state, "element_balance_error", float("nan"))
    if not converged:
        return GateStatus("G5 Equilibrium Valid", False,
                          "Gibbs 最小化が収束しませんでした",
                          "⚠️", "provisional")
    if math.isfinite(err) and err > 1e-6:
        return GateStatus("G5 Equilibrium Valid", False,
                          f"元素保存誤差 {err:.2e} > 1e-6",
                          "⚠️", "provisional")
    return GateStatus("G5 Equilibrium Valid", True, "", "✅", "ok")


def _gate_g6(prior: Iterable[GateStatus]) -> GateStatus:
    prior_list = list(prior)
    blockers = [p for p in prior_list if not p.passed]
    if blockers:
        return GateStatus("G6 Research Valid", False,
                          f"{len(blockers)} 個のゲートが未通過",
                          "⛔", "locked",
                          "; ".join(b.name for b in blockers))
    return GateStatus("G6 Research Valid", True, "", "✅", "ok",
                      "論文・レポートに使用可能")


def evaluate_gates(*, validation=None, bundle=None, spec_bp=None,
                   thermo_state=None, equilibrium_state=None) -> list[GateStatus]:
    """Return the 6 gate statuses in order G1 → G6."""
    g1 = _gate_g1(validation)
    g2 = _gate_g2(bundle)
    g3 = _gate_g3(spec_bp)
    g4 = _gate_g4(thermo_state, g3)
    g5 = _gate_g5(equilibrium_state, g4)
    g6 = _gate_g6([g1, g2, g3, g4, g5])
    return [g1, g2, g3, g4, g5, g6]
