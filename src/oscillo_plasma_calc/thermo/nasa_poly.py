"""NASA 7- and 9-coefficient polynomial evaluators.

NASA 7 (Cantera default, GRI-Mech, USC II):
    Cp/R = a1 + a2 T + a3 T^2 + a4 T^3 + a5 T^4
    H/(RT) = a1 + a2 T/2 + a3 T^2/3 + a4 T^3/4 + a5 T^4/5 + a6/T
    S/R   = a1 ln T + a2 T + a3 T^2/2 + a4 T^3/3 + a5 T^4/4 + a7

NASA 9 (CEA / NASA-RP-1311):
    Cp/R = a1 T^-2 + a2 T^-1 + a3 + a4 T + a5 T^2 + a6 T^3 + a7 T^4
    H/(RT) = -a1 T^-2 + a2 ln T / T + a3 + a4 T/2 + a5 T^2/3 + a6 T^3/4 + a7 T^4/5 + b1/T
    S/R   = -a1 T^-2 / 2 - a2 T^-1 + a3 ln T + a4 T + a5 T^2/2 + a6 T^3/3 + a7 T^4/4 + b2

Both forms support multiple temperature ranges (typically 2 for NASA7,
3 for NASA9). The evaluator picks the right range automatically and
emits a clear error if T is outside any defined range.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class NASA7Range:
    Tmin: float
    Tmax: float
    a: tuple[float, ...]   # length 7

    def __post_init__(self) -> None:
        if len(self.a) != 7:
            raise ValueError(f"NASA7 needs 7 coefficients, got {len(self.a)}")


@dataclass(frozen=True)
class NASA7:
    """Standard NASA 7-coefficient form, two temperature ranges (low/high)."""
    name: str
    low: NASA7Range
    high: NASA7Range

    def _select(self, T: float) -> NASA7Range:
        if self.low.Tmin <= T <= self.low.Tmax:
            return self.low
        if self.high.Tmin <= T <= self.high.Tmax:
            return self.high
        raise ValueError(
            f"T={T:.4g} K outside NASA7 range "
            f"[{self.low.Tmin}, {self.high.Tmax}] for {self.name}"
        )

    def cp_R(self, T: float) -> float:
        a = self._select(T).a
        return a[0] + a[1]*T + a[2]*T**2 + a[3]*T**3 + a[4]*T**4

    def h_RT(self, T: float) -> float:
        a = self._select(T).a
        return a[0] + a[1]*T/2 + a[2]*T**2/3 + a[3]*T**3/4 + a[4]*T**4/5 + a[5]/T

    def s_R(self, T: float) -> float:
        a = self._select(T).a
        return (a[0]*math.log(T) + a[1]*T + a[2]*T**2/2
                + a[3]*T**3/3 + a[4]*T**4/4 + a[6])

    def g_RT(self, T: float) -> float:
        return self.h_RT(T) - self.s_R(T)


@dataclass(frozen=True)
class NASA9Range:
    Tmin: float
    Tmax: float
    a: tuple[float, ...]   # length 7
    b: tuple[float, float] # integration constants (b1, b2)

    def __post_init__(self) -> None:
        if len(self.a) != 7:
            raise ValueError(f"NASA9 needs 7 a-coefficients, got {len(self.a)}")
        if len(self.b) != 2:
            raise ValueError(f"NASA9 needs 2 b-constants, got {len(self.b)}")


@dataclass(frozen=True)
class NASA9:
    """NASA 9-coefficient form, multiple temperature ranges (typically 3).

    Used by NASA CEA and the standard NASA Glenn ThermoBuild output.
    """
    name: str
    ranges: tuple[NASA9Range, ...]

    def _select(self, T: float) -> NASA9Range:
        for r in self.ranges:
            if r.Tmin <= T <= r.Tmax:
                return r
        Tmin = self.ranges[0].Tmin
        Tmax = self.ranges[-1].Tmax
        raise ValueError(
            f"T={T:.4g} K outside NASA9 range [{Tmin}, {Tmax}] for {self.name}"
        )

    def cp_R(self, T: float) -> float:
        r = self._select(T)
        a = r.a
        return (a[0]/T**2 + a[1]/T + a[2] + a[3]*T + a[4]*T**2
                + a[5]*T**3 + a[6]*T**4)

    def h_RT(self, T: float) -> float:
        r = self._select(T)
        a = r.a; b = r.b
        return (-a[0]/T**2 + a[1]*math.log(T)/T + a[2] + a[3]*T/2
                + a[4]*T**2/3 + a[5]*T**3/4 + a[6]*T**4/5 + b[0]/T)

    def s_R(self, T: float) -> float:
        r = self._select(T)
        a = r.a; b = r.b
        return (-a[0]/(2*T**2) - a[1]/T + a[2]*math.log(T) + a[3]*T
                + a[4]*T**2/2 + a[5]*T**3/3 + a[6]*T**4/4 + b[1])

    def g_RT(self, T: float) -> float:
        return self.h_RT(T) - self.s_R(T)
