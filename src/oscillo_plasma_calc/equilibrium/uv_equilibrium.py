"""UV equilibrium: internal energy + volume → T + P + composition.

Strategy: outer bisection on T, inner TP at each step. The pressure is
recomputed from the ideal-gas law each iteration:

    P(T) = n_total(T) · R · T / V

The objective is the internal-energy residual:

    f(T) = Σ_i n_i(T, P(T)) · [h_i(T) - R T] − U_target

(using U = H − PV = H − n R T for an ideal-gas mixture).

Used to model a closed plasma bubble: pulse energy is injected at
fixed volume, so the bubble heats and pressurises until equilibrium.
"""
from __future__ import annotations

from dataclasses import dataclass

from scipy.optimize import brentq

from .tp_equilibrium import equilibrium_tp, EquilibriumResult, R_J_per_mol_K


@dataclass
class UVResult:
    converged: bool
    T_K: float
    P_Pa: float
    V_m3: float
    composition: EquilibriumResult
    U_target_J: float
    U_final_J: float
    iterations: int
    message: str = ""


def _internal_energy_J(comp: EquilibriumResult) -> float:
    """U = Σ n_i · (h_i - R T) = Σ n_i · R T · (h/RT - 1).  Ideal gas."""
    from ..thermo import lookup
    U = 0.0
    for name, n in comp.moles.items():
        e = lookup(name)
        if e is None:
            continue
        h_RT = e.evaluator.h_RT(comp.T_K)
        U += n * R_J_per_mol_K * comp.T_K * (h_RT - 1.0)
    return U


def equilibrium_uv(species, U_target_J: float, V_m3: float,
                    reactants: dict[str, float],
                    *, T_guess_low: float = 300.0,
                    T_guess_high: float = 6000.0,
                    xtol: float = 1.0,
                    max_iter: int = 100) -> UVResult:
    """Solve UV equilibrium by 1-D bisection on T (P solved from ideal-gas law)."""
    species_list = list(species)

    def residual(T: float) -> float:
        # First-pass pressure from total reactant moles (will be refined by inner TP)
        n_total_guess = sum(reactants.values()) or 1.0
        P_guess = n_total_guess * R_J_per_mol_K * T / V_m3
        comp = equilibrium_tp(species_list, T, P_guess, reactants)
        if not comp.converged:
            return 1e30
        n_total_real = sum(comp.moles.values())
        # Pressure consistent with the equilibrated total moles
        P_consistent = n_total_real * R_J_per_mol_K * T / V_m3
        if abs(P_consistent - P_guess) / max(P_guess, 1e-30) > 0.05:
            comp = equilibrium_tp(species_list, T, P_consistent, reactants)
        U = _internal_energy_J(comp)
        return U - U_target_J

    f_lo = residual(T_guess_low)
    f_hi = residual(T_guess_high)
    if f_lo * f_hi > 0:
        return UVResult(
            converged=False, T_K=float("nan"), P_Pa=float("nan"), V_m3=V_m3,
            composition=equilibrium_tp(species_list, T_guess_low,
                                         101325.0, reactants),
            U_target_J=U_target_J, U_final_J=float("nan"),
            iterations=0,
            message=(f"U target {U_target_J:.3g} J not bracketed by "
                     f"[T={T_guess_low}, T={T_guess_high}]"),
        )
    try:
        T_root, info = brentq(residual, T_guess_low, T_guess_high,
                                xtol=xtol, maxiter=max_iter,
                                full_output=True, disp=False)
    except Exception as exc:
        return UVResult(
            converged=False, T_K=float("nan"), P_Pa=float("nan"), V_m3=V_m3,
            composition=equilibrium_tp(species_list, T_guess_low,
                                         101325.0, reactants),
            U_target_J=U_target_J, U_final_J=float("nan"),
            iterations=0, message=f"brentq error: {exc}",
        )
    n_total_initial = sum(reactants.values()) or 1.0
    P_first = n_total_initial * R_J_per_mol_K * T_root / V_m3
    final = equilibrium_tp(species_list, T_root, P_first, reactants)
    n_total_final = sum(final.moles.values())
    P_final = n_total_final * R_J_per_mol_K * T_root / V_m3
    if abs(P_final - P_first) / max(P_first, 1e-30) > 0.05:
        final = equilibrium_tp(species_list, T_root, P_final, reactants)
    U_final = _internal_energy_J(final)
    return UVResult(
        converged=info.converged and final.converged,
        T_K=float(T_root), P_Pa=float(P_final), V_m3=V_m3,
        composition=final, U_target_J=U_target_J, U_final_J=U_final,
        iterations=int(info.iterations),
        message="ok",
    )
