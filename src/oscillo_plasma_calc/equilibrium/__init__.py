"""CEA-like chemical equilibrium engine (Phase 6 minimum implementation).

Currently provides:
- TP (temperature, pressure) equilibrium via SLSQP Gibbs minimization
- Element-balance constraints
- Returns mole fractions for the requested species set

Not yet implemented (deferred per docs/2026-05-02_phase5_nasa_integration_plan.md):
- HP / UV problem types
- Element-potential method (CEA's Newton-Raphson) — currently SLSQP fallback
- Condensed phase insertion test
- Transport properties (γ, c_p, μ)
"""
from .tp_equilibrium import equilibrium_tp, EquilibriumResult
from .hp_equilibrium import equilibrium_hp, HPResult
from .uv_equilibrium import equilibrium_uv, UVResult
from .condensed_phase import (
    evaluate_condensed_insertion, CondensedTestResult, DEFAULT_CANDIDATES,
)

__all__ = [
    "equilibrium_tp", "EquilibriumResult",
    "equilibrium_hp", "HPResult",
    "equilibrium_uv", "UVResult",
    "evaluate_condensed_insertion", "CondensedTestResult", "DEFAULT_CANDIDATES",
]
