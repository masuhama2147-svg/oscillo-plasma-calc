"""Wilhoit high-temperature extrapolation for Cp.

NASA RP-1271 §3.4 introduced the Wilhoit form to avoid the unphysical
Cp values that result when low-temperature NASA polynomials are
extrapolated linearly into the high-temperature regime.

Functional form:
    Cp/R = a + (b - a) y^2 [ 1 + (y - 1)(c0 + c1 y + c2 y^2 + c3 y^3) ]
    y    = T / (T + B)

Boundary behaviour:
    - T → 0:    y → 0  ⇒  Cp/R → a   (low-T limit, e.g. 2.5 for monatomic)
    - T → ∞:    y → 1  ⇒  Cp/R → b   (high-T limit per equipartition)

The integral forms for H/RT and S/R follow analytically (RP-1271 Eqs 27-29).

Two use modes
-------------
1. Construct from explicit (a, b, B, c0..c3) — direct evaluation
2. `fit_wilhoit_to_nasa(nasa, T_high, b)` — fit B and c0..c3 so the Wilhoit
   form matches a NASA polynomial up to its Tmax, then extrapolate beyond.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence

import numpy as np
from scipy.optimize import least_squares


@dataclass(frozen=True)
class WilhoitCp:
    """Wilhoit Cp/R as a function of temperature.

    Parameters
    ----------
    a : low-temperature limit of Cp/R (e.g. 2.5 for monatomic, 3.5 for diatomic
        rigid-rotor without vibration)
    b : high-temperature limit of Cp/R (full equipartition)
    B : scaling parameter [K]; determines where the transition between
        a and b takes place (typical 500–1500 K)
    c : tuple (c0, c1, c2, c3) — shape parameters
    name : optional label for diagnostic output
    Tmin, Tmax : valid range (informational; the form is well-defined at any T > 0)
    """
    a: float
    b: float
    B: float
    c: tuple[float, float, float, float]
    name: str = ""
    Tmin: float = 0.0
    Tmax: float = 6000.0

    def _y(self, T: float) -> float:
        return T / (T + self.B)

    def cp_R(self, T: float) -> float:
        if T <= 0:
            return self.a
        y = self._y(T)
        c0, c1, c2, c3 = self.c
        poly = c0 + c1 * y + c2 * y**2 + c3 * y**3
        return self.a + (self.b - self.a) * y**2 * (1.0 + (y - 1.0) * poly)

    def cp_R_array(self, T: np.ndarray) -> np.ndarray:
        T = np.asarray(T, dtype=float)
        out = np.empty_like(T)
        for i, t in enumerate(T.flat):
            out.flat[i] = self.cp_R(float(t))
        return out


def fit_wilhoit_to_nasa(nasa, *,
                         T_fit_lo: float = 200.0,
                         T_fit_hi: float | None = None,
                         a: float = 2.5,
                         b: float = 4.5,
                         n_points: int = 50,
                         B0: float = 500.0,
                         c0: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0),
                         ) -> WilhoitCp:
    """Fit Wilhoit (B, c0..c3) so cp_R matches the NASA polynomial in [T_fit_lo, T_fit_hi].

    `a` and `b` are typically chosen by the caller from molecular structure:
    - monatomic gas:    a = 2.5,  b = 2.5
    - linear rigid:     a = 3.5,  b = 3.5 + N_vib
    - polyatomic:       a = 4.0,  b = 4.0 + N_vib

    For routine downstream use we default a=2.5, b=4.5 (suits diatomic ideal),
    but the caller should override for polyatomic species.
    """
    if T_fit_hi is None:
        # Use NASA's own Tmax if available, else 3500 K
        T_fit_hi = float(getattr(nasa, "high",
                                  getattr(nasa, "ranges", [None])[-1]).Tmax) \
            if hasattr(nasa, "high") or hasattr(nasa, "ranges") else 3500.0
    Ts = np.linspace(T_fit_lo, T_fit_hi, n_points)
    cp_target = np.array([nasa.cp_R(float(t)) for t in Ts])

    def residual(params: np.ndarray) -> np.ndarray:
        B = float(params[0])
        c = (float(params[1]), float(params[2]), float(params[3]), float(params[4]))
        if B <= 0:
            return np.full_like(cp_target, 1e6)
        wil = WilhoitCp(a=a, b=b, B=B, c=c)
        return np.array([wil.cp_R(float(t)) - cp_t for t, cp_t in zip(Ts, cp_target)])

    x0 = np.array([B0, *c0], dtype=float)
    try:
        result = least_squares(residual, x0, method="lm", max_nfev=2000)
        B = float(result.x[0])
        c = (float(result.x[1]), float(result.x[2]),
             float(result.x[3]), float(result.x[4]))
    except Exception:
        # Conservative fallback: pure step from a → b at B0
        B = B0
        c = (0.0, 0.0, 0.0, 0.0)

    name = getattr(nasa, "name", "")
    return WilhoitCp(
        a=a, b=b, B=B, c=c, name=name,
        Tmin=T_fit_lo, Tmax=20000.0,    # extrapolated regime
    )


def cp_R_extrapolated(nasa, T_K: float, *,
                      a: float = 2.5, b: float = 4.5,
                      cache: dict | None = None) -> float:
    """Evaluate Cp/R at T_K using NASA inside its valid range, Wilhoit beyond.

    Optional `cache` is a per-species dict to avoid re-fitting Wilhoit on
    every call; pass an external dict if you want shared caching.
    """
    Tmax = (getattr(nasa, "high", None).Tmax
            if hasattr(nasa, "high")
            else nasa.ranges[-1].Tmax)
    if T_K <= Tmax:
        return nasa.cp_R(T_K)
    key = id(nasa)
    if cache is not None and key in cache:
        wil = cache[key]
    else:
        wil = fit_wilhoit_to_nasa(nasa, a=a, b=b)
        if cache is not None:
            cache[key] = wil
    return wil.cp_R(T_K)
