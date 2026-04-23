"""Oil-synthesis specific KPIs (CO₂ reduction → liquid fuel).

References:
- Snoeckx & Bogaerts 2017 Chem Soc Rev 46:5805 (SEI standard definition)
- Bogaerts & Neyts 2018 ACS Energy Lett 3:1013
- Fridman 2008 Plasma Chemistry (energy-cost definitions)
"""
from __future__ import annotations

import math

from ..report.trace import TraceResult
from ..report.ui_format import format_si, pretty_number
from ..config.constants import N_AVOGADRO


def specific_energy_input(E_plasma_J: float, n_CO2_mol: float) -> TraceResult:
    """SEI = E_plasma / n_CO2 [kJ/mol]. Primary CO₂-plasma literature metric."""
    if n_CO2_mol <= 0 or E_plasma_J <= 0:
        return TraceResult(
            name="Specific Energy Input (SEI)",
            value=float("nan"), unit="kJ/mol",
            equation_latex=r"\mathrm{SEI} = E_\mathrm{plasma}/n_{\mathrm{CO}_2}",
        )
    sei = (E_plasma_J / 1000.0) / n_CO2_mol
    # eV/molecule でも表示
    sei_eV = (E_plasma_J / n_CO2_mol) / N_AVOGADRO * 6.242e18
    return TraceResult(
        name="Specific Energy Input (SEI)",
        value=sei, unit="kJ/mol",
        equation_latex=r"\mathrm{SEI} = \dfrac{E_\mathrm{plasma}}{n_{\mathrm{CO}_2}}",
        substitution_latex=(
            fr"\mathrm{{SEI}} = \dfrac{{{format_si(E_plasma_J, 'J')}}}"
            fr"{{{pretty_number(n_CO2_mol)}\,\text{{mol}}}} "
            fr"= {pretty_number(sei)}\,\text{{kJ/mol}} "
            fr"\;({pretty_number(sei_eV)}\,\text{{eV/molecule}})"
        ),
        steps=["CO₂ プラズマ化学の universal 指標",
               "典型: 300〜1000 kJ/mol (3〜10 eV/molecule)"],
        sources=["Snoeckx & Bogaerts 2017 CSR 46:5805"],
    )


def energy_cost(E_plasma_J: float, n_product_mol: float) -> TraceResult:
    """EC = E_plasma / n_product [kJ/mol] or [kWh/kg if mass given]."""
    if n_product_mol <= 0 or E_plasma_J <= 0:
        return TraceResult(
            name="Energy cost EC",
            value=float("nan"), unit="kJ/mol",
            equation_latex=r"\mathrm{EC} = E_\mathrm{plasma}/n_\mathrm{prod}",
        )
    ec = (E_plasma_J / 1000.0) / n_product_mol
    return TraceResult(
        name="Energy cost EC",
        value=ec, unit="kJ/mol",
        equation_latex=r"\mathrm{EC} = \dfrac{E_\mathrm{plasma}}{n_\mathrm{prod}}",
        substitution_latex=(
            fr"\mathrm{{EC}} = \dfrac{{{format_si(E_plasma_J, 'J')}}}"
            fr"{{{pretty_number(n_product_mol)}\,\text{{mol}}}} "
            fr"= {pretty_number(ec)}\,\text{{kJ/mol}}"
        ),
        steps=["1 mol の目的生成物に要した投入エネルギー"],
        sources=["Bogaerts & Neyts 2018 ACS Energy Lett 3:1013"],
    )


def co2_conversion_rate(n_CO2_in_mol: float,
                         n_CO2_out_mol: float) -> TraceResult:
    """χ_CO2 = (n_in − n_out) / n_in × 100 %."""
    if n_CO2_in_mol <= 0:
        return TraceResult(
            name="CO₂ conversion rate χ",
            value=float("nan"), unit="%",
            equation_latex=r"\chi_{\mathrm{CO}_2} = (n_\mathrm{in}-n_\mathrm{out})/n_\mathrm{in}",
        )
    chi = (n_CO2_in_mol - n_CO2_out_mol) / n_CO2_in_mol * 100.0
    return TraceResult(
        name="CO₂ conversion rate χ",
        value=chi, unit="%",
        equation_latex=(
            r"\chi_{\mathrm{CO}_2} = "
            r"\dfrac{n_\mathrm{in}-n_\mathrm{out}}{n_\mathrm{in}}\times 100\%"
        ),
        substitution_latex=(
            fr"\chi = \dfrac{{{pretty_number(n_CO2_in_mol)} - "
            fr"{pretty_number(n_CO2_out_mol)}}}{{{pretty_number(n_CO2_in_mol)}}}"
            fr"\times 100\% = {pretty_number(chi)}\,\%"
        ),
        steps=["反応器入口・出口の GC 定量値から算出"],
        sources=["Snoeckx & Bogaerts 2017 CSR 46:5805"],
    )


def single_pass_energy_efficiency(chi_percent: float,
                                   delta_H_kJ_per_mol: float,
                                   sei_kJ_per_mol: float) -> TraceResult:
    """η_SE = χ · ΔH / SEI — single-pass energy efficiency."""
    if sei_kJ_per_mol <= 0:
        return TraceResult(
            name="Single-pass energy efficiency η_SE",
            value=float("nan"), unit="%",
            equation_latex=r"\eta_\mathrm{SE} = \chi\,\Delta H/\mathrm{SEI}",
        )
    eta = (chi_percent / 100.0) * delta_H_kJ_per_mol / sei_kJ_per_mol * 100.0
    return TraceResult(
        name="Single-pass energy efficiency η_SE",
        value=eta, unit="%",
        equation_latex=(
            r"\eta_\mathrm{SE} = "
            r"\dfrac{\chi_{\mathrm{CO}_2}\,\Delta H_r}{\mathrm{SEI}}"
        ),
        substitution_latex=(
            fr"\eta_\mathrm{{SE}} = \dfrac{{{pretty_number(chi_percent)}\%"
            fr" \times {pretty_number(delta_H_kJ_per_mol)}\,\text{{kJ/mol}}}}"
            fr"{{{pretty_number(sei_kJ_per_mol)}\,\text{{kJ/mol}}}} "
            fr"= {pretty_number(eta)}\,\%"
        ),
        steps=["η_chem の別表現（χ と SEI が既知ならこちらが直接）"],
        sources=["Snoeckx & Bogaerts 2017 CSR 46:5805"],
    )


def asf_chain_probability(product_distribution: dict[int, float]) -> TraceResult:
    """Anderson-Schulz-Flory α: ln(W_n/n) = n·ln(α) + const.

    `product_distribution`: {carbon_number: weight_fraction}
    """
    import numpy as np
    items = [(n, w) for n, w in product_distribution.items() if n > 0 and w > 0]
    if len(items) < 2:
        return TraceResult(
            name="ASF chain growth probability α",
            value=float("nan"), unit="(fraction)",
            equation_latex=r"\ln(W_n/n) = n\,\ln\alpha + C",
            steps=["有効データ点 < 2"],
        )
    xs = np.array([n for n, _ in items], dtype=float)
    ys = np.array([math.log(w / n) for n, w in items])
    m, _ = np.polyfit(xs, ys, 1)
    alpha = float(math.exp(m))
    return TraceResult(
        name="ASF chain growth probability α",
        value=alpha, unit="(fraction)",
        equation_latex=r"\ln\!\left(\dfrac{W_n}{n}\right) = n\ln\alpha + C",
        substitution_latex=(
            fr"\alpha = \exp({pretty_number(m)}) = {pretty_number(alpha)}"
        ),
        steps=[f"データ点 n={len(items)}",
               "FT 合成で α=0.8〜0.95 がディーゼル域、>0.95 で wax"],
        sources=["Anderson 1984, 'The Fischer-Tropsch Synthesis'"],
    )
