"""Top-level orchestration: Waveform → full Tier-1 electrical analysis.

Keeps the UI and CLI in sync by centralizing which calculations run together.
"""
from __future__ import annotations

from dataclasses import dataclass

from .io_layer import Waveform
from .electrical import (
    instantaneous_power, peak_power,
    absorbed_energy, mean_power,
    v_rms, i_rms,
    lissajous_power,
)
from .signal.peaks import detect_vpp, detect_ipp, rise_time, slew_rate
from .signal.fft import dominant_frequency
from .report.trace import TraceResult
from .qa.anomaly import classify
from .electrical.advanced import (
    pulse_energy as _adv_pulse_energy,
    duty_cycle as _adv_duty,
    effective_average_power as _adv_p_eff,
    abs_power_mean as _adv_abs_p,
    crest_factor as _adv_cf,
    form_factor as _adv_ff,
)
from .qa.operational import device_power_budget, DEFAULT_BUDGET_W


# Mapping from TraceResult.name (stable part) → (explanation_key, anomaly_key, category)
_BINDING = {
    "Peak-to-peak voltage Vpp":               ("vpp", "vpp", "electrical"),
    "Peak-to-peak current Ipp":               ("ipp", "ipp", "electrical"),
    "Rise time t_r":                          ("rise_time", "rise_time", "electrical"),
    "Peak slew rate dV/dt":                   ("slew_rate_v", "slew_rate_v", "electrical"),
    "Peak slew rate dI/dt":                   ("slew_rate_i", "slew_rate_i", "electrical"),
    "Instantaneous power P(t)":               ("instant_power", None, "electrical"),
    "Peak instantaneous power |P|_max":       ("peak_power", "peak_power", "electrical"),
    "Absorbed energy E (∫ V·I dt)":           ("energy", "energy", "electrical"),
    "Time-average power P̄":                  ("mean_power", "mean_power", "electrical"),
    "Voltage RMS Vrms":                       ("v_rms", "v_rms", "electrical"),
    "Current RMS Irms":                       ("i_rms", "i_rms", "electrical"),
    "Lissajous (V–q) mean power":             ("lissajous", None, "electrical"),
    "Instantaneous impedance Z(t)":           ("impedance", None, "electrical"),
    # Advanced
    "Energy per pulse E_pulse":               ("pulse_energy", "pulse_energy", "electrical"),
    "Duty cycle D":                            ("duty_cycle", "duty_cycle", "electrical"),
    "Effective average power (Ppeak·D)":      ("effective_average_power",
                                                "effective_average_power", "electrical"),
    "Absolute instantaneous power time-average ⟨|P|⟩":
                                               ("abs_power_mean", "abs_power_mean",
                                                "electrical"),
    "Crest factor CF (voltage)":              ("crest_factor", "crest_factor", "electrical"),
    "Form factor FF (voltage)":               ("form_factor", "form_factor", "electrical"),
    "Plasma power density p_vol":             ("power_density", "power_density", "electrical"),
    # Operational
    "Device-wide power budget margin":        ("budget_margin", None, "operational"),
    "Heat dissipation requirement Q_cool":    ("heat_dissipation", None, "operational"),
    "Device-to-plasma efficiency η_dev":      ("eta_device", "eta_device", "operational"),
    # Plasma (non-eq)
    "Reduced electric field E/N":             ("e_over_n", "e_over_n", "plasma"),
    "Mean electron energy":                    ("mean_e_energy", "mean_e_energy", "plasma"),
    "Non-equilibrium ratio T_e/T_gas":         ("tv_rot_ratio", "tv_rot_ratio", "plasma"),
    "Vibrational temperature Tv":              ("t_vib", "t_vib", "plasma"),
    # Chemistry
    "Specific Energy Input (SEI)":            ("sei", "sei", "chemistry"),
    "Energy cost EC":                          ("energy_cost", "energy_cost", "chemistry"),
    "CO₂ conversion rate χ":                   ("chi_co2", "chi_co2", "chemistry"),
    "Single-pass energy efficiency η_SE":     ("eta_se", "eta_se", "chemistry"),
    "ASF chain growth probability α":         ("asf", "asf", "chemistry"),
    "G value":                                 ("g_value", "g_value", "chemistry"),
    "Chemical energy-conversion efficiency η": ("efficiency", "efficiency", "chemistry"),
    "Product selectivity X_target":            ("selectivity", None, "chemistry"),
    # Existing plasma tier-2
    "Electron temperature Te":                 ("boltzmann_two_line", "boltzmann_two_line",
                                                "plasma"),
    "Electron density n_e":                    ("stark", "stark_ne", "plasma"),
    "Debye length λ_D":                        ("debye", "debye", "plasma"),
    "Electron plasma frequency f_p":           ("plasma_freq", "plasma_freq", "plasma"),
    "Ohmic heating density p_ohm":             ("ohmic", None, "plasma"),
    "Paschen breakdown voltage V_b":           ("paschen", "paschen", "plasma"),
    "Excitation temperature Te":               ("excitation_temp", "excitation_temp_K",
                                                "plasma"),
}


def _bind(tr: TraceResult) -> TraceResult:
    """Attach explanation_key + anomaly + category to a TraceResult in-place."""
    for prefix, (ek, ak, cat) in _BINDING.items():
        if tr.name.startswith(prefix):
            tr.explanation_key = ek
            tr.category = cat
            if ak is not None:
                s = tr.scalar()
                if s is not None:
                    tr.anomaly = classify(ak, s)
            break
    return tr


@dataclass
class AnalysisBundle:
    waveform: Waveform
    vpp: TraceResult
    ipp: TraceResult
    v_rise: TraceResult
    slew_v: TraceResult
    slew_i: TraceResult
    p_inst: TraceResult
    p_peak: TraceResult
    energy: TraceResult
    p_mean: TraceResult
    v_rms_r: TraceResult
    i_rms_r: TraceResult
    lissajous: TraceResult
    dominant_freq_v: float
    # advanced
    pulse_e: TraceResult | None = None
    duty: TraceResult | None = None
    p_eff: TraceResult | None = None
    abs_p_avg: TraceResult | None = None
    crest: TraceResult | None = None
    form: TraceResult | None = None
    # operational
    budget: TraceResult | None = None

    def as_list(self) -> list[TraceResult]:
        core = [
            self.vpp, self.ipp, self.v_rise,
            self.slew_v, self.slew_i,
            self.p_inst, self.p_peak,
            self.energy, self.p_mean,
            self.v_rms_r, self.i_rms_r,
            self.lissajous,
        ]
        adv = [t for t in (self.pulse_e, self.duty, self.p_eff,
                           self.abs_p_avg, self.crest, self.form,
                           self.budget) if t is not None]
        return core + adv


def analyze_electrical(wf: Waveform,
                       pulse_rep_freq_hz: float | None = None,
                       device_budget_W: float = DEFAULT_BUDGET_W) -> AnalysisBundle:
    bundle = AnalysisBundle(
        waveform=wf,
        vpp=detect_vpp(wf.v),
        ipp=detect_ipp(wf.i),
        v_rise=rise_time(wf.t, wf.v),
        slew_v=slew_rate(wf.t, wf.v, label="V"),
        slew_i=slew_rate(wf.t, wf.i, label="I"),
        p_inst=instantaneous_power(wf.v, wf.i),
        p_peak=peak_power(wf.v, wf.i),
        energy=absorbed_energy(wf.t, wf.v, wf.i),
        p_mean=mean_power(wf.t, wf.v, wf.i),
        v_rms_r=v_rms(wf.t, wf.v),
        i_rms_r=i_rms(wf.t, wf.i),
        lissajous=lissajous_power(wf.t, wf.v, wf.i, pulse_rep_freq_hz),
        dominant_freq_v=dominant_frequency(wf.v, wf.dt),
    )
    # Advanced quantities（会議 2026-04-23 要件）
    bundle.pulse_e = _adv_pulse_energy(wf.t, wf.v, wf.i)
    bundle.duty = _adv_duty(wf.t, wf.v)
    duty_val = bundle.duty.scalar() or 0.0
    bundle.p_eff = _adv_p_eff(wf.v, wf.i, duty_val)
    bundle.abs_p_avg = _adv_abs_p(wf.t, wf.v, wf.i)
    bundle.crest = _adv_cf(wf.v)
    bundle.form = _adv_ff(wf.v)
    # 装置予算チェック（1 kW ライン）
    p_eff_val = bundle.p_eff.scalar() or 0.0
    bundle.budget = device_power_budget(p_eff_val, budget_W=device_budget_W)

    for tr in bundle.as_list():
        _bind(tr)
    return bundle
