"""Single source of truth for every physical equation used in the software.

All formulas are declared symbolically (sympy) so the UI and PDF report can
render the full derivation: raw equation → numeric substitution → value.

Returned `sympy.Eq` objects can be fed to `sympy.latex(...)` directly.
"""
from __future__ import annotations

from dataclasses import dataclass
import sympy as sp


@dataclass
class Equation:
    key: str
    title: str
    expr: sp.Eq
    description: str
    sources: list[str]

    @property
    def latex(self) -> str:
        return sp.latex(self.expr)


# ---- Tier 1: Electrical ----
t, V, I, P, Pbar, E_abs, T_period, f_Hz = sp.symbols(
    "t V I P \\bar{P} E T f", positive=False, real=True)
V_k, I_k, dt = sp.symbols("V_k I_k \\Delta t", real=True)

EQ_INSTANT_POWER = Equation(
    key="instant_power",
    title="瞬時電力 (instantaneous power)",
    expr=sp.Eq(sp.Function("P")(t), sp.Function("V")(t) * sp.Function("I")(t)),
    description="Discharge instantaneous power at each sample.",
    sources=["2006_JJAP-45-8864", "2011_PSST-20-034016"],
)

EQ_ABSORBED_ENERGY = Equation(
    key="absorbed_energy",
    title="吸収エネルギー (absorbed energy)",
    expr=sp.Eq(E_abs, sp.Integral(sp.Function("V")(t) * sp.Function("I")(t),
                                  (t, 0, T_period))),
    description="Time integral of V·I over one observation window.",
    sources=["2008_APEX-1-046002"],
)

EQ_MEAN_POWER = Equation(
    key="mean_power",
    title="平均電力 (time-average power)",
    expr=sp.Eq(Pbar, E_abs / T_period),
    description="Absorbed energy divided by window duration.",
    sources=["2008_APEX-1-046002"],
)

V_rms, I_rms = sp.symbols("V_{rms} I_{rms}", positive=True)
EQ_VRMS = Equation(
    key="v_rms",
    title="電圧実効値 (RMS voltage)",
    expr=sp.Eq(V_rms, sp.sqrt(sp.Integral(sp.Function("V")(t) ** 2,
                                          (t, 0, T_period)) / T_period)),
    description="Root-mean-square voltage.",
    sources=["classical AC circuit theory"],
)
EQ_IRMS = Equation(
    key="i_rms",
    title="電流実効値 (RMS current)",
    expr=sp.Eq(I_rms, sp.sqrt(sp.Integral(sp.Function("I")(t) ** 2,
                                          (t, 0, T_period)) / T_period)),
    description="Root-mean-square current.",
    sources=["classical AC circuit theory"],
)

q = sp.Symbol("q", real=True)
EQ_LISSAJOUS = Equation(
    key="lissajous",
    title="Lissajous 平均電力 (Manley 法)",
    expr=sp.Eq(Pbar, f_Hz * sp.Integral(sp.Function("V")(t), q)),
    description="DBD-style mean power: pulse-rep frequency × closed V-q loop area.",
    sources=["Manley 1943", "2013_CAP-13-1050"],
)

Z = sp.Function("Z")(t)
EQ_IMPEDANCE = Equation(
    key="impedance",
    title="瞬時インピーダンス",
    expr=sp.Eq(Z, sp.Function("V")(t) / sp.Function("I")(t)),
    description="Instantaneous ratio; guard against I≈0.",
    sources=["classical AC circuit theory"],
)

Vpp, Ipp, Vmax, Vmin, Imax, Imin = sp.symbols(
    "V_{pp} I_{pp} V_{\\max} V_{\\min} I_{\\max} I_{\\min}", real=True)
EQ_VPP = Equation(
    key="vpp",
    title="ピーク間電圧 Vpp",
    expr=sp.Eq(Vpp, Vmax - Vmin),
    description="Peak-to-peak voltage.",
    sources=["2013_CAP-13-1050"],
)
EQ_IPP = Equation(
    key="ipp",
    title="ピーク間電流 Ipp",
    expr=sp.Eq(Ipp, Imax - Imin),
    description="Peak-to-peak current.",
    sources=["2013_CAP-13-1050"],
)


# ---- Tier 2: Plasma ----
T_e, n_e, epsilon0, k_B, e_ch, m_e, lambda_D, f_p = sp.symbols(
    "T_e n_e \\varepsilon_0 k_B e m_e \\lambda_D f_p", positive=True)
I_ij, I_kl, g_i, g_k, A_ij, A_kl, nu_ij, nu_kl, Ei, Ek = sp.symbols(
    "I_{ij} I_{kl} g_i g_k A_{ij} A_{kl} \\nu_{ij} \\nu_{kl} E_i E_k",
    positive=True)

EQ_BOLTZMANN = Equation(
    key="boltzmann",
    title="Boltzmann 分布による電子温度 Te",
    expr=sp.Eq(I_ij / I_kl,
               (g_i * A_ij * nu_ij) / (g_k * A_kl * nu_kl) *
               sp.exp(-(Ei - Ek) / (k_B * T_e))),
    description="Two-line intensity ratio → Te (optical emission spectroscopy).",
    sources=["2006_JJAP-45-8864", "2009_JAP-106-113302"],
)

alpha_stark, dlambda = sp.symbols(r"\alpha \Delta\lambda_{1/2}", positive=True)
EQ_STARK = Equation(
    key="stark",
    title="Stark 広がりによる電子密度 ne",
    expr=sp.Eq(n_e, alpha_stark * dlambda ** sp.Rational(3, 2)),
    description="H_α line FWHM (Δλ_{1/2}) → electron density.",
    sources=["2009_POP-16-033503"],
)

EQ_DEBYE = Equation(
    key="debye",
    title="Debye 長",
    expr=sp.Eq(lambda_D, sp.sqrt(epsilon0 * k_B * T_e / (n_e * e_ch ** 2))),
    description="Screening length of quasi-neutral plasma.",
    sources=["classical plasma physics"],
)

EQ_PLASMA_FREQ = Equation(
    key="plasma_freq",
    title="プラズマ周波数 f_p",
    expr=sp.Eq(f_p, 1 / (2 * sp.pi) * sp.sqrt(n_e * e_ch ** 2 / (m_e * epsilon0))),
    description="Natural oscillation frequency of electron plasma.",
    sources=["2008_APEX-1-046002"],
)

sigma, E_field, p_ohm = sp.symbols("\\sigma E p_\\mathrm{ohm}", positive=True)
EQ_OHMIC = Equation(
    key="ohmic",
    title="Ohmic 加熱密度",
    expr=sp.Eq(p_ohm, sigma * E_field ** 2),
    description="Volumetric Ohmic power in a conductive liquid plasma.",
    sources=["2011_PSST-20-034016"],
)

V_break, A_p, B_p, p_gas, d_gap, gamma_se = sp.symbols(
    "V_b A B p d \\gamma", positive=True)
EQ_PASCHEN = Equation(
    key="paschen",
    title="Paschen 破壊電圧",
    expr=sp.Eq(V_break, (B_p * p_gas * d_gap) /
               (sp.log(A_p * p_gas * d_gap) - sp.log(sp.log(1 + 1 / gamma_se)))),
    description="Gas-discharge breakdown voltage as a function of pd.",
    sources=["2013_CAP-13-1050"],
)


# ---- Tier 3: Chemistry ----
n_prod, E_abs_eV, G_val = sp.symbols("n_\\mathrm{prod} E_\\mathrm{abs} G",
                                     positive=True)
EQ_G_VALUE = Equation(
    key="g_value",
    title="G 値 (生成率)",
    expr=sp.Eq(G_val, n_prod / (E_abs_eV / 100)),
    description="Molecules produced per 100 eV absorbed.",
    sources=["2012_IJHE-37-16000", "2020_JJIE_99-104"],
)

DeltaH, E_plasma, eta_chem = sp.symbols(r"\Delta H E_\mathrm{plasma} \eta_\mathrm{chem}",
                                        positive=True)
EQ_EFFICIENCY = Equation(
    key="efficiency",
    title="化学効率",
    expr=sp.Eq(eta_chem, DeltaH * n_prod / E_plasma),
    description="Chemical energy output / plasma input energy.",
    sources=["2017_JEPE-10-335"],
)

n_k, n_total, X_k = sp.symbols("n_k n_\\mathrm{total} X_k", positive=True)
EQ_SELECTIVITY = Equation(
    key="selectivity",
    title="選択性",
    expr=sp.Eq(X_k, n_k / n_total),
    description="Mole fraction of target species among all products.",
    sources=["2019_IJHE_44-23912"],
)


EQUATIONS: dict[str, Equation] = {
    eq.key: eq for eq in [
        EQ_INSTANT_POWER, EQ_ABSORBED_ENERGY, EQ_MEAN_POWER,
        EQ_VRMS, EQ_IRMS, EQ_LISSAJOUS, EQ_IMPEDANCE, EQ_VPP, EQ_IPP,
        EQ_BOLTZMANN, EQ_STARK, EQ_DEBYE, EQ_PLASMA_FREQ, EQ_OHMIC, EQ_PASCHEN,
        EQ_G_VALUE, EQ_EFFICIENCY, EQ_SELECTIVITY,
    ]
}


def get_equation(key: str) -> Equation:
    return EQUATIONS[key]
