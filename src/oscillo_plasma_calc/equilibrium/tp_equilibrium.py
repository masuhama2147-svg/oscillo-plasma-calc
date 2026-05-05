"""CEA-like TP (temperature, pressure) chemical equilibrium.

Solves: minimize G/(RT) = Σ n_i [μ_i°(T)/RT + ln(x_i) + ln(P/P0)]
        subject to: Σ a_ki n_i = b_k  (element balance)
                    n_i ≥ 0

Uses SLSQP from scipy.optimize as the first-pass implementation. The
NASA CEA reference (RP-1311) uses an element-potential Newton-Raphson
method which is faster but more complex; we defer that to a later
milestone (M3 in the Phase 5+ roadmap).

Numerical safeguards:
- Lower-bound mole numbers at 1e-30 (avoids log(0))
- Element-balance residual reported alongside the solution
- Returns `converged=False` if SLSQP exits without success
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable

import numpy as np
from scipy.optimize import minimize

from ..thermo import lookup
from ..thermo.database import SpeciesEntry


R_J_per_mol_K = 8.314462618
P_REF = 101325.0   # Pa, NASA reference pressure


@dataclass
class EquilibriumResult:
    converged: bool
    species: list[str]
    mole_fractions: dict[str, float]
    moles: dict[str, float]
    T_K: float
    P_Pa: float
    element_balance_error: float           # max relative residual
    iterations: int
    final_gibbs_RT: float
    message: str = ""
    warnings: list[str] = field(default_factory=list)


def _build_element_matrix(entries: list[SpeciesEntry]) -> tuple[np.ndarray, list[str]]:
    elements: list[str] = []
    for e in entries:
        for el in e.species.formula:
            if el not in elements:
                elements.append(el)
    A = np.zeros((len(elements), len(entries)))
    for j, e in enumerate(entries):
        for i, el in enumerate(elements):
            A[i, j] = e.species.formula.get(el, 0)
    return A, elements


def _initial_n(entries: list[SpeciesEntry], reactants: dict[str, float]) -> np.ndarray:
    """Initial guess: all species equal-distribution of total moles."""
    total = sum(reactants.values())
    if total <= 0:
        total = 1.0
    return np.full(len(entries), total / len(entries))


def equilibrium_tp(species: Iterable[str],
                    T_K: float,
                    P_Pa: float,
                    reactants: dict[str, float],
                    *,
                    max_iter: int = 200) -> EquilibriumResult:
    """Compute TP equilibrium via Gibbs minimization.

    Parameters
    ----------
    species : iterable of species names allowed in the equilibrium pool.
    T_K     : temperature in Kelvin.
    P_Pa    : pressure in Pascal.
    reactants : initial mole inventory keyed by element symbol, e.g.
                {"C": 1.0, "O": 2.0, "H": 4.0} sets the element balance.
    """
    species_list = list(species)
    entries: list[SpeciesEntry] = []
    warnings: list[str] = []
    for name in species_list:
        e = lookup(name)
        if e is None:
            warnings.append(f"unknown species '{name}' (skipped)")
            continue
        if not e.species.is_in_temperature_range(T_K):
            warnings.append(
                f"{name} outside Tmin/Tmax ({e.species.Tmin}-{e.species.Tmax})"
            )
            continue
        entries.append(e)

    if len(entries) < 2:
        return EquilibriumResult(
            converged=False, species=[], mole_fractions={}, moles={},
            T_K=T_K, P_Pa=P_Pa, element_balance_error=float("nan"),
            iterations=0, final_gibbs_RT=float("nan"),
            message="need ≥ 2 valid species", warnings=warnings,
        )

    A, elements = _build_element_matrix(entries)
    # Element balance vector b
    b = np.zeros(len(elements))
    for el, mol in reactants.items():
        if el not in elements:
            warnings.append(f"reactant element {el} not in any species (ignored)")
            continue
        b[elements.index(el)] = mol

    # G_i°/RT for each species at T
    g_RT = np.array([e.evaluator.g_RT(T_K) for e in entries])
    log_PR = math.log(P_Pa / P_REF)

    def gibbs_objective(n: np.ndarray) -> float:
        n = np.maximum(n, 1e-30)
        n_total = np.sum(n)
        x = n / n_total
        # G/RT = Σ n_i [μ_i°/RT + ln(x_i) + ln(P/P0)]
        return float(np.sum(n * (g_RT + np.log(x) + log_PR)))

    def gibbs_grad(n: np.ndarray) -> np.ndarray:
        n = np.maximum(n, 1e-30)
        n_total = np.sum(n)
        x = n / n_total
        return g_RT + np.log(x) + log_PR

    constraints = [
        {"type": "eq", "fun": lambda n, k=k: float(A[k] @ n - b[k]),
         "jac": lambda n, k=k: A[k]}
        for k in range(len(elements))
    ]
    n0 = _initial_n(entries, reactants)
    bounds = [(1e-30, None)] * len(entries)

    res = minimize(
        gibbs_objective, n0, jac=gibbs_grad, method="SLSQP",
        bounds=bounds, constraints=constraints,
        options={"maxiter": max_iter, "ftol": 1e-9},
    )

    n_final = np.maximum(res.x, 1e-30)
    total = float(np.sum(n_final))
    mol_fractions = {entries[i].species.name: float(n_final[i] / total)
                     for i in range(len(entries))}
    moles = {entries[i].species.name: float(n_final[i])
             for i in range(len(entries))}

    # element balance residual
    residual = A @ n_final - b
    rel_err = float(np.max(np.abs(residual) / np.maximum(np.abs(b), 1e-30)))

    return EquilibriumResult(
        converged=bool(res.success),
        species=[e.species.name for e in entries],
        mole_fractions=mol_fractions,
        moles=moles,
        T_K=T_K, P_Pa=P_Pa,
        element_balance_error=rel_err,
        iterations=int(res.nit),
        final_gibbs_RT=float(res.fun),
        message=str(res.message),
        warnings=warnings,
    )
