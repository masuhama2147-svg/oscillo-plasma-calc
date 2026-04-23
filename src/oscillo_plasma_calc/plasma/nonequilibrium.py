"""Non-equilibrium plasma diagnostic quantities.

References:
- Fridman 2008 "Plasma Chemistry" (non-eq theory)
- Bruggeman et al. 2014 PSST 23:045022 (plasma-liquid, T_rot / T_vib diagnostics)
- Phelps LXCat database (cross sections for E/N → ⟨ε⟩)
"""
from __future__ import annotations

import math

from ..report.trace import TraceResult
from ..report.ui_format import format_si, pretty_number
from ..config.constants import K_B, E_CHARGE


TOWNSEND = 1e-21       # 1 Td = 1e-21 V·m² (≡ E/N unit)


def number_density_from_pt(pressure_Pa: float, T_gas_K: float) -> float:
    """Ideal-gas number density [m^-3]."""
    if T_gas_K <= 0:
        return float("nan")
    return pressure_Pa / (K_B * T_gas_K)


def reduced_electric_field(E_Vm: float,
                            pressure_Pa: float = 101325.0,
                            T_gas_K: float = 300.0) -> TraceResult:
    """E/N in Townsend units (Td). Cornerstone of EEDF analysis."""
    n = number_density_from_pt(pressure_Pa, T_gas_K)
    if not math.isfinite(n) or n <= 0:
        return TraceResult(
            name="Reduced electric field E/N",
            value=float("nan"), unit="Td",
            equation_latex=r"E/N = E / n_\mathrm{gas}",
        )
    e_over_n = E_Vm / n                          # V·m²
    td = e_over_n / TOWNSEND                     # Td
    return TraceResult(
        name="Reduced electric field E/N",
        value=td, unit="Td",
        equation_latex=r"E/N = \dfrac{E}{n_\mathrm{gas}}\;[\text{V·m}^2]",
        substitution_latex=(
            fr"E/N = \dfrac{{{pretty_number(E_Vm)}\,\text{{V/m}}}}"
            fr"{{{pretty_number(n)}\,\text{{m}}^{{-3}}}} "
            fr"= {pretty_number(td)}\,\text{{Td}}"
        ),
        steps=[f"n_gas = p/(kB T) = {n:.3e} m^-3 (p={pressure_Pa/1e3:.1f} kPa, T={T_gas_K:.1f} K)",
               "1 Td = 1e-21 V·m²",
               "典型 CO₂ プラズマ: 50〜300 Td"],
        sources=["Phelps LXCat", "Fridman 2008"],
        extra={"n_gas": n},
    )


def mean_electron_energy(EN_Td: float) -> TraceResult:
    """Empirical fit for CO₂ background (Ridenti et al. 2015 heuristic).

    ⟨ε⟩ [eV] ≈ 0.02 · (E/N [Td]) for E/N < 200 Td (rough).
    This is a provisional fit; a BOLSIG+ solve is recommended for real use.
    """
    if not math.isfinite(EN_Td) or EN_Td <= 0:
        return TraceResult(
            name="Mean electron energy ⟨ε⟩",
            value=float("nan"), unit="eV",
            equation_latex=r"\langle\varepsilon\rangle \approx 0.02\cdot(E/N)",
        )
    mean_eV = 0.02 * EN_Td
    return TraceResult(
        name="Mean electron energy ⟨ε⟩ (estimate)",
        value=mean_eV, unit="eV",
        equation_latex=r"\langle\varepsilon\rangle \approx 0.02\,(E/N)\;[\text{eV/Td}]",
        substitution_latex=(
            fr"\langle\varepsilon\rangle \approx 0.02 \times {pretty_number(EN_Td)} "
            fr"= {pretty_number(mean_eV)}\,\text{{eV}}"
        ),
        steps=["粗近似。精密には BOLSIG+ を回すこと（本ソフトは目安値）",
               "CO₂ 電離閾値 13.8 eV / 解離 5.5 eV と比較"],
        sources=["Ridenti et al. 2015 PSST (heuristic)"],
    )


def non_equilibrium_ratio(T_e_K: float, T_gas_K: float) -> TraceResult:
    """T_e / T_gas — 'non-equilibrium ratio'. CO₂ 還元に有利 ⇔ 非平衡度 > 10."""
    if T_gas_K <= 0:
        return TraceResult(
            name="Non-equilibrium ratio T_e/T_gas",
            value=float("nan"), unit="(ratio)",
            equation_latex=r"T_e / T_\mathrm{gas}",
        )
    ratio = T_e_K / T_gas_K
    return TraceResult(
        name="Non-equilibrium ratio T_e/T_gas",
        value=ratio, unit="(ratio)",
        equation_latex=r"\dfrac{T_e}{T_\mathrm{gas}}",
        substitution_latex=(
            fr"\dfrac{{{pretty_number(T_e_K)}\,\text{{K}}}}"
            fr"{{{pretty_number(T_gas_K)}\,\text{{K}}}} = {pretty_number(ratio)}"
        ),
        steps=["> 10 ⇔ 強い非平衡（CO₂ 還元に有利）",
               "≈ 1 ⇔ 熱平衡（エネルギー効率低下）"],
        sources=["Fridman 2008 Plasma Chemistry"],
    )


def vibrational_temperature_from_ratio(I_high: float, I_low: float,
                                        dE_vib_eV: float = 0.291) -> TraceResult:
    """Tv from 2-band vibrational intensity ratio (Boltzmann analog).

    I_high/I_low = exp(-dE/(k_B Tv))  ⇒  Tv = -dE/(k_B ln(I_h/I_l))
    dE_vib_eV: vibrational quantum energy (default: CO₂ asymmetric stretch 2349 cm^-1 ≈ 0.291 eV).
    """
    import math as _m
    if I_high <= 0 or I_low <= 0:
        return TraceResult(
            name="Vibrational temperature Tv",
            value=float("nan"), unit="K",
            equation_latex=r"T_v = -\dfrac{\Delta E_v}{k_B \ln(I_h/I_l)}",
        )
    r = I_high / I_low
    if r >= 1.0:
        return TraceResult(
            name="Vibrational temperature Tv",
            value=float("inf"), unit="K",
            equation_latex=r"T_v = -\dfrac{\Delta E_v}{k_B \ln(I_h/I_l)}",
            steps=["I_h/I_l >= 1 — Boltzmann 分布不成立（自己吸収または逆転分布の疑い）"],
        )
    # use kB in eV/K for direct eV input
    kB_eV = K_B / E_CHARGE
    Tv = -dE_vib_eV / (kB_eV * _m.log(r))
    return TraceResult(
        name="Vibrational temperature Tv",
        value=Tv, unit="K",
        equation_latex=r"T_v = -\dfrac{\Delta E_v}{k_B\,\ln(I_h/I_l)}",
        substitution_latex=(
            fr"T_v = -\dfrac{{{pretty_number(dE_vib_eV)}\,\text{{eV}}}}"
            fr"{{k_B\ln({pretty_number(r)})}} = {pretty_number(Tv)}\,\text{{K}}"
        ),
        steps=["CO₂ プラズマで Tv ≫ T_gas ⇔ 非熱的 CO₂ 還元モード",
               "典型 Tv = 2000〜6000 K"],
        sources=["Bruggeman et al. 2014 PSST 23:045022",
                 "Fridman 2008 Plasma Chemistry"],
    )
