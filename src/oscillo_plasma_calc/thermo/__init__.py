"""NASA PAC91-style thermodynamic engine.

Phase 5 skeleton (2026-05-02). Provides:
- NASA 7- and 9-coefficient polynomial evaluators (cp, h, s, g)
- Species dataclass with temperature ranges + provenance
- Wilhoit high-temperature extrapolation (RP-1271 §3.4)
- Equilibrium constant K(T) from ΔG_f

Not yet implemented (deferred to later milestones, see
docs/2026-05-02_phase5_nasa_integration_plan.md):
- Partition-function evaluators for di-atomic / poly-atomic species
- Group additivity (Benson) fallback for unknown species
- Direct Q(T) → NASA poly fitter
"""
from .species import Species
from .nasa_poly import NASA7, NASA9
from .equilibrium_constants import log10_K_from_dG

__all__ = ["Species", "NASA7", "NASA9", "log10_K_from_dG"]
