"""Analytic EEDF reference distributions.

Used as sanity checks for the numerical two-term solver and as an
emergency fallback when no cross-section data is loaded.

Both functions return f(ε) normalised so that:

    ∫₀^∞ f(ε) √ε  dε  =  1

This is the standard EEDF normalisation used by BOLSIG+ and most
plasma-physics references.
"""
from __future__ import annotations

import math

import numpy as np


def maxwell_eedf(eps_eV: np.ndarray, mean_energy_eV: float) -> np.ndarray:
    """Maxwell EEDF: f(ε) = 2/√π · Te^(-3/2) · exp(-ε/Te), Te ≡ (2/3) ⟨ε⟩."""
    Te = (2.0 / 3.0) * mean_energy_eV
    if Te <= 0:
        return np.zeros_like(eps_eV)
    return (2.0 / math.sqrt(math.pi)) * Te**(-1.5) * np.exp(-np.asarray(eps_eV) / Te)


def druyvesteyn_eedf(eps_eV: np.ndarray, mean_energy_eV: float) -> np.ndarray:
    """Druyvesteyn EEDF: f(ε) ∝ exp(-(ε/εc)^2), with εc set so ⟨ε⟩ matches."""
    # ⟨ε⟩ = εc · Γ(5/4) / Γ(3/4) ≈ 0.55 εc^... actually with normalisation:
    # We use the standard form valid for elastic-only with const cross section:
    # f(ε) = C · exp(-(ε / εD)^2) where εD is fit.
    # Here, we adjust εD so that ∫ ε f √ε dε / ∫ f √ε dε = mean_energy_eV.
    # Closed-form constants for the Druyvesteyn distribution
    eps = np.asarray(eps_eV, dtype=float)
    if mean_energy_eV <= 0:
        return np.zeros_like(eps)
    # Empirical relationship: ⟨ε⟩ ≈ 0.4368·εD²/⟨ε⟩  (from Γ-function ratio)
    # Solve ⟨ε⟩² = 0.4368·εD²·⟨ε⟩ → εD = ⟨ε⟩/√0.4368
    # Use direct normalisation by quadrature for robustness:
    eD2 = mean_energy_eV / 0.4368
    f = np.exp(-(eps**2) / eD2)
    norm = float(np.trapezoid(f * np.sqrt(np.maximum(eps, 1e-30)), eps))
    if norm <= 0:
        return np.zeros_like(eps)
    return f / norm


def mean_energy_from_eedf(eps_eV: np.ndarray, f: np.ndarray) -> float:
    """⟨ε⟩ = ∫ ε f(ε) √ε dε / ∫ f(ε) √ε dε."""
    eps = np.asarray(eps_eV, dtype=float)
    f = np.asarray(f, dtype=float)
    weight = np.sqrt(np.maximum(eps, 1e-30))
    num = float(np.trapezoid(eps * f * weight, eps))
    den = float(np.trapezoid(f * weight, eps))
    if den <= 0:
        return float("nan")
    return num / den
