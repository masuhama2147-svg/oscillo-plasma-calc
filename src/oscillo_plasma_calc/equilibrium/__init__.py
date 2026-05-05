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

__all__ = ["equilibrium_tp", "EquilibriumResult"]
