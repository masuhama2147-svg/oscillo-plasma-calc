"""Pure-Python two-term spherical-harmonics Boltzmann solver.

Solves the steady-state EEDF f(ε) for electrons in a weakly ionised gas
under uniform reduced electric field E/N. The two-term approximation
expands f(v) into isotropic f₀(ε) and a small anisotropic correction f₁,
and reduces to a single second-order ODE for f₀(ε):

    d/dε [ (E/N)² · ε / (3·Q_m(ε)) · df₀/dε ]
        + d/dε [ ε² · 2·m_e/M · Q_m(ε) · ( f₀ + k_B·T_g/e · df₀/dε ) ]
        − Σᵢ εᵢ · Q_excᵢ(ε) · f₀  =  0

with f₀ → 0 as ε → ∞ and ∫ f₀(ε) √ε dε = 1.

This is the classical Holstein-Margenau formulation (Hagelaar & Pitchford
2005, PSST 14:722, the BOLSIG+ paper). The tridiagonal discretisation
matches §3 of that paper.

Limitations
-----------
- Two-term approximation breaks at high E/N where the EEDF becomes very
  anisotropic (~1000 Td and above). Issue a warning then.
- Inelastic collisions handled via aggregate threshold loss only; no
  cascade.
- Designed for accuracy ~10–20 % vs full BOLSIG+, sufficient for triage
  but not for definitive cross-section-resolved chemistry.

For paper-grade EEDF on Linux/Windows users should still install the
official BOLSIG+ binary; this Python solver is the M4-Mac fallback.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Physical constants
_M_E = 9.1093837015e-31    # kg
_E   = 1.602176634e-19     # C
_K_B = 1.380649e-23        # J/K


@dataclass
class TwoTermResult:
    eps_eV: np.ndarray         # energy grid [eV]
    f0: np.ndarray             # normalised EEDF, ∫ f₀ √ε dε = 1
    mean_energy_eV: float
    drift_velocity_m_s: float  # μ·E
    rate_coefficients: dict[str, float]  # process_name → k [m^3/s]
    converged: bool
    warnings: list[str]


def solve_two_term(*, EN_Td: float,
                    momentum_xs,                # callable: ε [eV] → Q_m [m^2]
                    inelastic_xs: dict | None = None,
                    M_amu: float = 28.0,        # bath gas molar mass (N2 default)
                    T_gas_K: float = 300.0,
                    eps_max_eV: float = 30.0,
                    n_grid: int = 200,
                    ) -> TwoTermResult:
    """Solve the two-term Boltzmann equation on a uniform energy grid.

    Parameters
    ----------
    EN_Td       : reduced electric field [Townsend]
    momentum_xs : function ε [eV] → momentum-transfer cross section [m^2]
    inelastic_xs : optional dict {process_name: (threshold_eV, callable)}
                   where callable returns Q [m^2] at given ε [eV]
    M_amu       : bath-gas molar mass [g/mol] (default 28 = N₂)
    T_gas_K     : gas temperature [K]
    eps_max_eV  : grid upper bound (use 30 eV for moderate E/N, 50 eV for high)
    n_grid      : number of grid points

    Returns
    -------
    TwoTermResult with f₀, ⟨ε⟩, drift velocity and per-process rate coefficients.
    """
    inelastic_xs = inelastic_xs or {}

    eps = np.linspace(1e-6, eps_max_eV, n_grid)
    deps = float(eps[1] - eps[0])
    EN_Vm2 = EN_Td * 1e-21                    # 1 Td = 1e-21 V·m²
    M_kg = M_amu * 1e-3 / 6.02214076e23       # kg per molecule

    # Vectorised cross sections
    Qm = np.array([float(momentum_xs(e)) for e in eps])
    Qm = np.maximum(Qm, 1e-25)                 # avoid divide-by-zero

    # Inelastic loss term (aggregated)
    inel_loss = np.zeros_like(eps)
    for name, (eth, func) in inelastic_xs.items():
        for k, e in enumerate(eps):
            if e >= eth:
                inel_loss[k] += eth * float(func(e))

    # Build tridiagonal system (Hagelaar 2005 §3 simplified form):
    #   A·f₀ = 0 with f₀(eps_max) = 0 and normalisation row replacing the first.
    n = len(eps)
    main = np.zeros(n); upper = np.zeros(n); lower = np.zeros(n)
    # E-field-driven diffusion in energy + elastic momentum-transfer drift:
    D = (EN_Vm2 ** 2) * eps / (3.0 * Qm)
    elastic_drift = (eps**2) * 2.0 * _M_E / M_kg * Qm
    # Thermal diffusion (small)
    Dth = elastic_drift * (_K_B * T_gas_K / _E)

    for k in range(1, n - 1):
        a = (D[k] + Dth[k]) / deps**2
        b = elastic_drift[k] / (2.0 * deps)
        lower[k] = a - b
        main[k]  = -2.0 * a - inel_loss[k]
        upper[k] = a + b
    # Boundary conditions
    main[-1] = 1.0
    main[0] = 1.0
    upper[0] = 0.0
    lower[-1] = 0.0
    rhs = np.zeros(n)
    rhs[0] = 1.0    # arbitrary scale; will be renormalised

    # Solve tridiagonal
    try:
        from scipy.linalg import solve_banded
        ab = np.zeros((3, n))
        ab[0, 1:] = upper[:-1]
        ab[1, :]  = main
        ab[2, :-1] = lower[1:]
        f0 = solve_banded((1, 1), ab, rhs)
        converged = True
        warnings: list[str] = []
    except Exception as exc:
        f0 = np.exp(-eps / 2.0)               # graceful Maxwellian fallback
        converged = False
        warnings = [f"tridiagonal solver failed: {exc}; using Maxwell fallback"]

    # Enforce non-negativity then normalise: ∫ f₀ √ε dε = 1
    f0 = np.maximum(f0, 0.0)
    weight = np.sqrt(np.maximum(eps, 1e-30))
    norm = float(np.trapezoid(f0 * weight, eps))
    if norm <= 0:
        f0 = np.exp(-eps / 2.0)
        norm = float(np.trapezoid(f0 * weight, eps))
        warnings.append("EEDF non-positive; substituted Maxwellian.")
    f0 /= norm

    mean_eV = float(np.trapezoid(eps * f0 * weight, eps))

    # Velocity v(ε) = √(2 e ε / m_e). Drift velocity from f₁ (anisotropic).
    v = np.sqrt(2.0 * _E * eps / _M_E)
    drift = -(EN_Vm2 / 3.0) * float(
        np.trapezoid(v / Qm * np.gradient(f0, eps) * weight, eps)
    )

    # Rate coefficients per inelastic process
    rates: dict[str, float] = {}
    for name, (eth, func) in inelastic_xs.items():
        Q = np.array([float(func(e)) if e >= eth else 0.0 for e in eps])
        rates[name] = float(np.trapezoid(v * Q * f0 * weight, eps))

    if EN_Td > 1000:
        warnings.append(
            f"E/N = {EN_Td} Td is high; two-term approximation may be inaccurate"
        )

    return TwoTermResult(
        eps_eV=eps, f0=f0,
        mean_energy_eV=mean_eV,
        drift_velocity_m_s=drift,
        rate_coefficients=rates,
        converged=converged,
        warnings=warnings,
    )
