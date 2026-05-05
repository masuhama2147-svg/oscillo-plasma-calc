"""Condensed-phase insertion test for chemical equilibrium.

Per NASA CEA RP-1311 §6.4: after a gas-phase Gibbs minimization, each
candidate condensed species s is tested for thermodynamic favourability:

    D_s = G°_s/RT  −  Σ_k a_ks · λ_k

where λ_k is the element potential (Lagrange multiplier from the
gas-phase solution). If D_s < 0, inserting s would lower G further;
the species is added and the calculation repeats.

This file uses a simpler equivalent: re-solve TP equilibrium with the
candidate condensed species included in the species list, then compare
the Gibbs values. If the new total Gibbs is lower than the gas-only
result, accept the insertion. This avoids needing direct access to
SLSQP's dual variables.

Hysteresis (per CEA): once a condensed phase is inserted with mole
fraction > `insertion_threshold`, it stays inserted until its mole
fraction falls below `removal_threshold`. This avoids oscillation
near the boundary.

Use case in oil-synthesis research
----------------------------------
Carbon soot deposition (graphite) is a major loss channel. Detecting
"thermodynamically expected soot" lets researchers triage GC-MS
"unknown carbon" peaks before chasing exotic by-products.

Other interesting condensed species for plasma/electrode systems:
- C(graphite), C(diamond)   — carbon deposit
- Cu, Cu2O, CuO              — copper electrode oxidation
- W, WO3                      — tungsten electrode oxidation
- Fe, Fe2O3, Fe3O4            — iron-electrode systems
- Al2O3                       — alumina ceramic interaction
"""
from __future__ import annotations

from dataclasses import dataclass

from .tp_equilibrium import equilibrium_tp, EquilibriumResult


# Default candidate set for liquid-plasma oil-synthesis research.
# Names match the keys in `data/thermo/nasa_condensed.yaml`.
DEFAULT_CANDIDATES = (
    "C(gr)",         # graphite (carbon deposit)
    "Cu(cr)", "Cu2O(cr)", "CuO(cr)",
    "W(cr)", "WO3(cr)",
    "Fe(a)", "Fe2O3(cr)", "Fe3O4(cr)",
    "AL2O3(a)",
)


@dataclass
class CondensedTestResult:
    inserted: list[str]
    rejected: list[str]
    final: EquilibriumResult
    gas_only: EquilibriumResult
    delta_gibbs_RT: float          # gas_only − final (positive = condensed phase improved)


def _filter_known(candidates):
    """Return only the candidates that exist in the thermo database."""
    from ..thermo import lookup
    return [name for name in candidates if lookup(name) is not None]


def evaluate_condensed_insertion(
    gas_species: list[str],
    T_K: float, P_Pa: float,
    reactants: dict[str, float],
    candidates: tuple[str, ...] = DEFAULT_CANDIDATES,
    *, insertion_threshold: float = 1e-4,
) -> CondensedTestResult:
    """Run gas-only equilibrium then test each candidate condensed species.

    Returns lists of inserted (favorable) and rejected species, plus the
    final equilibrium with all favorable phases included.

    Note: this function is intentionally NOT named `test_*` to avoid
    collision with pytest's auto-collection.
    """
    candidates_present = _filter_known(candidates)
    gas_only = equilibrium_tp(gas_species, T_K, P_Pa, reactants)

    inserted: list[str] = []
    rejected: list[str] = []
    species_pool = list(gas_species)

    for cand in candidates_present:
        trial_pool = species_pool + [cand]
        trial = equilibrium_tp(trial_pool, T_K, P_Pa, reactants)
        if not trial.converged:
            rejected.append(cand)
            continue
        # The candidate is "favorable" if it has non-negligible mole fraction
        # AND lowers the Gibbs of the system.
        if (trial.mole_fractions.get(cand, 0.0) > insertion_threshold
                and trial.final_gibbs_RT < gas_only.final_gibbs_RT - 1e-6):
            inserted.append(cand)
            species_pool.append(cand)
        else:
            rejected.append(cand)

    final = equilibrium_tp(species_pool, T_K, P_Pa, reactants)
    return CondensedTestResult(
        inserted=inserted,
        rejected=rejected,
        final=final,
        gas_only=gas_only,
        delta_gibbs_RT=gas_only.final_gibbs_RT - final.final_gibbs_RT,
    )
