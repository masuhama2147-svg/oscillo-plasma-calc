"""LaTeX-safe formatting helpers for human-readable numeric substitution.

`pretty_number(3.8e11)`       → `3.80\\times 10^{11}`
`format_si(11840, 'V')`       → `11.84\\,\\text{kV}`
`format_si(0.0187787, 'J')`   → `18.78\\,\\text{mJ}`
`format_si(2.43e-6, 's')`     → `2.43\\,\\text{\\mu s}`
`format_si(3.8e11, 'V/s')`    → `3.80\\times 10^{11}\\,\\text{V/s}`

The helpers never depend on matplotlib or JS; they only emit plain LaTeX so
KaTeX / MathJax can render them.
"""
from __future__ import annotations

import math


_SI_PREFIX = [
    (1e12,  "T"),
    (1e9,   "G"),
    (1e6,   "M"),
    (1e3,   "k"),
    (1.0,   ""),
    (1e-3,  "m"),
    (1e-6,  "\\mu "),
    (1e-9,  "n"),
    (1e-12, "p"),
]

# Units for which SI-prefix scaling is *not* physically conventional.
_NO_PREFIX_UNITS = {
    "", "K", "eV", "%", "Hz",                # leave Hz to use scientific when huge
    "molecules/100 eV", "(mole fraction)",
}

_COMPOUND_UNITS = {"V/s", "A/s", "W/m^3", "W/m^2", "m^-3", "1/m^3", "Ω"}


def pretty_number(value: float, sig: int = 4) -> str:
    """Return a LaTeX-ready numeric token.

    - finite |value| ∈ [1e-3, 1e4): plain float with `sig` significant digits.
    - otherwise: mantissa + `\\times 10^{exp}` with `sig-1` digits on the mantissa.
    - ±inf / NaN: ``\\text{inf}`` / ``\\text{NaN}``.
    """
    if not math.isfinite(value):
        return r"\text{NaN}" if math.isnan(value) else r"\text{inf}"
    if value == 0:
        return "0"
    mag = abs(value)
    if 1e-3 <= mag < 1e4:
        return f"{value:.{sig}g}"
    mantissa, exponent = f"{value:.{sig - 1}e}".split("e")
    return fr"{mantissa}\times 10^{{{int(exponent)}}}"


def format_si(value: float, unit: str, sig: int = 4) -> str:
    """Return ``<number>\\,\\text{<unit>}`` using SI prefix where reasonable.

    Compound units (V/s, W/m^3, Ω) keep scientific notation instead of attempting
    to prefix the unit.
    """
    if not math.isfinite(value):
        token = pretty_number(value, sig)
        return fr"{token}\,\text{{{unit}}}"
    if value == 0:
        return fr"0\,\text{{{unit}}}"
    if unit in _NO_PREFIX_UNITS or unit in _COMPOUND_UNITS:
        return fr"{pretty_number(value, sig)}\,\text{{{unit}}}"

    mag = abs(value)
    for factor, prefix in _SI_PREFIX:
        if mag >= factor * 0.999:
            scaled = value / factor
            return fr"{scaled:.{sig}g}\,\text{{{prefix}{unit}}}"
    # smaller than 1 pico — fall back to scientific
    return fr"{pretty_number(value, sig)}\,\text{{{unit}}}"


def fmt_eq(lhs: str, *parts: str) -> str:
    """Chain equation tokens: fmt_eq('V_{pp}', '3.68\\,\\text{kV} - (-3.12\\,\\text{kV})',
                                       '6.80\\,\\text{kV}') → 'V_{pp} = 3.68 ... = 6.80...'.
    """
    return f"{lhs} = " + " = ".join(parts)
