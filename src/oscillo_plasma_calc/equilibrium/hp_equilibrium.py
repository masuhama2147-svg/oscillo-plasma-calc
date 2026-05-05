"""HP equilibrium: enthalpy + pressure → temperature + composition.

Strategy: outer 1-D bisection on T, inner TP equilibrium at each candidate T.
The objective is the enthalpy residual:

    f(T) = Σ_i n_i(T, P) · h_i(T) − H_target

where n_i comes from the inner TP equilibrium. The Brent algorithm converges
in ≲ 30 iterations for typical combustion / plasma scenarios.

Used by the Equilibrium tab to estimate the adiabatic temperature reached
when an oscilloscope-measured pulse energy E is dumped into a CO2/H2 pool
at constant pressure (typical for an open reactor).
"""
from __future__ import annotations

from dataclasses import dataclass

from scipy.optimize import brentq

from .tp_equilibrium import equilibrium_tp, EquilibriumResult, R_J_per_mol_K


@dataclass
class HPResult:
    converged: bool
    T_K: float
    P_Pa: float
    composition: EquilibriumResult
    H_target_J: float
    H_final_J: float
    iterations: int
    message: str = ""


def _enthalpy_J(comp: EquilibriumResult) -> float:
    """Total enthalpy [J] = Σ n_i · h_i = Σ n_i · (h/RT) · R · T."""
    from ..thermo import lookup
    H = 0.0
    for name, n in comp.moles.items():
        e = lookup(name)
        if e is None:
            continue
        H += n * e.evaluator.h_RT(comp.T_K) * R_J_per_mol_K * comp.T_K
    return H


def equilibrium_hp(species, H_target_J: float, P_Pa: float,
                    reactants: dict[str, float],
                    *, T_guess_low: float = 300.0,
                    T_guess_high: float = 6000.0,
                    xtol: float = 1.0,
                    max_iter: int = 100) -> HPResult:
    """Solve HP equilibrium by 1-D bisection on temperature.

    Parameters
    ----------
    H_target_J : target total enthalpy [J] (e.g. pulse energy + initial enthalpy)
    P_Pa       : pressure
    reactants  : element inventory {element: moles}
    T_guess_low/high : bracket [K]; widen if the solver fails
    """
    species_list = list(species)

    def residual(T: float) -> float:
        comp = equilibrium_tp(species_list, T, P_Pa, reactants)
        if not comp.converged:
            return 1e30   # force Brent to step away from this T
        H = _enthalpy_J(comp)
        return H - H_target_J

    # Probe the bracket
    f_lo = residual(T_guess_low)
    f_hi = residual(T_guess_high)
    if f_lo * f_hi > 0:
        return HPResult(
            converged=False,
            T_K=float("nan"), P_Pa=P_Pa,
            composition=equilibrium_tp(species_list, T_guess_low, P_Pa, reactants),
            H_target_J=H_target_J, H_final_J=float("nan"),
            iterations=0,
            message=(f"H target {H_target_J:.3g} J not bracketed by "
                     f"[T={T_guess_low}, T={T_guess_high}] "
                     f"(residuals {f_lo:.3g}, {f_hi:.3g}) — widen T range"),
        )

    try:
        T_root, root_info = brentq(residual, T_guess_low, T_guess_high,
                                    xtol=xtol, maxiter=max_iter,
                                    full_output=True, disp=False)
    except Exception as exc:
        return HPResult(
            converged=False, T_K=float("nan"), P_Pa=P_Pa,
            composition=equilibrium_tp(species_list, T_guess_low, P_Pa, reactants),
            H_target_J=H_target_J, H_final_J=float("nan"),
            iterations=0, message=f"brentq error: {exc}",
        )
    final_comp = equilibrium_tp(species_list, T_root, P_Pa, reactants)
    H_final = _enthalpy_J(final_comp)
    # Sanity check: brentq may declare success at the bracket edge even if
    # residual is huge — guard against silent acceptance.
    H_residual_rel = abs(H_final - H_target_J) / max(abs(H_target_J), 1.0)
    converged_truly = (root_info.converged and final_comp.converged
                        and H_residual_rel < 1e-3)
    return HPResult(
        converged=converged_truly,
        T_K=float(T_root), P_Pa=P_Pa,
        composition=final_comp,
        H_target_J=H_target_J, H_final_J=H_final,
        iterations=int(root_info.iterations),
        message="ok" if converged_truly else "residual too large (target may be outside bracket)",
    )
