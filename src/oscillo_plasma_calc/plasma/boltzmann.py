"""Electron temperature from the Boltzmann-distribution two-line ratio method.

  I_ij / I_kl = (g_i A_ij ν_ij)/(g_k A_kl ν_kl) · exp[-(E_i-E_k)/(k_B T_e)]

References: Nomura lab 2006_JJAP-45-8864, 2009_JAP-106-113302.
"""
from __future__ import annotations

import math

from ..config.constants import K_B, E_CHARGE
from ..report.trace import TraceResult
from ..report.ui_format import pretty_number


def electron_temperature_boltzmann(
    I_ij: float, I_kl: float,
    g_i: float, g_k: float,
    A_ij: float, A_kl: float,
    nu_ij: float, nu_kl: float,
    E_i_eV: float, E_k_eV: float,
) -> TraceResult:
    """Solve Te (in eV) from a two-line intensity ratio."""
    dE_eV = E_i_eV - E_k_eV
    prefactor = (g_i * A_ij * nu_ij) / (g_k * A_kl * nu_kl)
    ratio = I_ij / I_kl
    if ratio <= 0 or prefactor <= 0:
        return TraceResult(name="Electron temperature Te",
                           value=float("nan"), unit="eV",
                           equation_latex="")
    # (I_ij/I_kl) / prefactor = exp(-dE/(kB Te))
    arg = ratio / prefactor
    if arg <= 0:
        return TraceResult(name="Electron temperature Te",
                           value=float("nan"), unit="eV",
                           equation_latex="")
    ln_arg = math.log(arg)
    if ln_arg == 0:
        return TraceResult(name="Electron temperature Te",
                           value=float("inf"), unit="eV",
                           equation_latex="")
    # -dE/(kB Te) = ln(arg)  →  Te = -dE / (kB ln(arg))    [J and K]
    Te_eV = -dE_eV / ln_arg  # because dE in eV and kB T_e in eV share the same unit
    return TraceResult(
        name="Electron temperature Te (Boltzmann plot)",
        value=Te_eV, unit="eV",
        equation_latex=(
            r"\frac{I_{ij}}{I_{kl}} = \frac{g_i A_{ij}\nu_{ij}}{g_k A_{kl}\nu_{kl}}"
            r"\exp\!\left[-\frac{E_i-E_k}{k_B T_e}\right]"
        ),
        substitution_latex=(
            fr"T_e = -\frac{{E_i-E_k}}{{\ln\!\left(\frac{{I_{{ij}}/I_{{kl}}}}"
            fr"{{\text{{prefactor}}}}\right)}} "
            fr"= -\frac{{{pretty_number(dE_eV)}\,\text{{eV}}}}"
            fr"{{\ln({pretty_number(arg)})}} "
            fr"= {pretty_number(Te_eV)}\,\text{{eV}}"
        ),
        steps=[
            f"prefactor = (g_i A_ij ν_ij)/(g_k A_kl ν_kl) = {prefactor:.4g}",
            f"I_ij/I_kl = {ratio:.4g}",
            f"arg = ratio/prefactor = {arg:.4g}",
            f"Te [K] ≈ {Te_eV * E_CHARGE / K_B:.4g}",
        ],
        sources=["2006_JJAP-45-8864", "2009_JAP-106-113302"],
    )
