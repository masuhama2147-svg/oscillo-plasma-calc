"""log10 K(T) from Gibbs free-energy change of reaction.

For a reaction νA·A + νB·B ⇌ νC·C + νD·D:

    ΔG_r°(T) = Σ ν_prod · G_prod(T) − Σ ν_react · G_react(T)
    log10 K(T) = -ΔG_r°(T) / (R·T·ln 10)

Used by the equilibrium engine and by the UI's "thermodynamic upper bound"
KPI in the Equilibrium tab (Phase 6).
"""
from __future__ import annotations

import math

R_J_per_mol_K = 8.314462618


def log10_K_from_dG(delta_G_J_per_mol: float, T_K: float) -> float:
    """Return log₁₀ K from ΔG (J/mol) and T (K)."""
    if T_K <= 0:
        raise ValueError(f"T must be positive, got {T_K}")
    return -delta_G_J_per_mol / (R_J_per_mol_K * T_K * math.log(10.0))


def K_from_dG(delta_G_J_per_mol: float, T_K: float) -> float:
    return 10.0 ** log10_K_from_dG(delta_G_J_per_mol, T_K)
