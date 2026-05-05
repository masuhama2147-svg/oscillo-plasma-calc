"""EEDF (electron energy distribution function) and electron-impact rates.

This package targets MacBook M4 Max (Apple Silicon) where the official
BOLSIG+ binary does not run natively. Instead we provide a Python-only
two-term Boltzmann solver for moderate-accuracy use, plus a generic
LXCat cross-section parser so the user can plug in published datasets.

Modules
-------
- two_term     : two-term spherical-harmonics Boltzmann solver
- lxcat_parser : LXCat .txt / .csv parser (Phelps, IST-Lisbon, etc.)
- eedf_table   : (E/N, gas-mix) → rate-coefficient table builder
- distributions: analytic EEDF (Maxwell, Druyvesteyn) for sanity checks
"""
from .distributions import maxwell_eedf, druyvesteyn_eedf, mean_energy_from_eedf
from .two_term import solve_two_term, TwoTermResult
from .lxcat_parser import parse_lxcat, CrossSection

__all__ = [
    "maxwell_eedf", "druyvesteyn_eedf", "mean_energy_from_eedf",
    "solve_two_term", "TwoTermResult",
    "parse_lxcat", "CrossSection",
]
