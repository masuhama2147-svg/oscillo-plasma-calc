"""Mole-fraction selectivity of a target product."""
from __future__ import annotations

from ..report.trace import TraceResult


def selectivity(n_target_mol: float, n_all_mol: dict[str, float]) -> TraceResult:
    total = sum(n_all_mol.values())
    if total <= 0:
        return TraceResult(name="Selectivity X_target",
                           value=float("nan"), unit="",
                           equation_latex=r"X_k = n_k/\sum_j n_j")
    X = n_target_mol / total
    return TraceResult(
        name="Product selectivity X_target",
        value=X, unit="(mole fraction)",
        equation_latex=r"X_k = \frac{n_k}{\sum_j n_j}",
        substitution_latex=fr"X = \frac{{{n_target_mol:.4g}}}{{{total:.4g}}} = {X:.4g}",
        steps=[f"all species: {n_all_mol}"],
        sources=["2019_IJHE_44-23912"],
    )
