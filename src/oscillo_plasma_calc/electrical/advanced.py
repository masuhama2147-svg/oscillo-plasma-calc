"""Advanced electrical quantities beyond Tier-1 basics.

Implements the "pulse-vs-window distinction" quantities requested at the
2026-04-23 lab meeting + classical pulse-shape indicators used in high-voltage
engineering.

All functions return `TraceResult` so they integrate cleanly with the Trace
tab and the Markdown / PDF exporters.
"""
from __future__ import annotations

import numpy as np
from scipy.signal import find_peaks
from scipy.integrate import trapezoid

from ..report.trace import TraceResult
from ..report.ui_format import format_si, pretty_number


# ---------------------------------------------------------- pulse detection

def detect_pulses(t: np.ndarray, v: np.ndarray,
                  min_prominence_ratio: float = 0.5,
                  min_distance_s: float = 100e-9,
                  ) -> tuple[np.ndarray, float, int]:
    """Return (peak_indices, fwhm_of_first_pulse_s, n_pulses).

    Tuned defaults for liquid-plasma ns-pulse waveforms:
      - prominence 0.5·Vpp — filters out sub-oscillations within a single event
      - distance    100 ns — min separation between distinct streamer events
    """
    v_abs = np.abs(v)
    vpp = float(np.ptp(v))
    if vpp <= 0 or t.size < 2:
        return np.array([], dtype=int), 0.0, 0
    prom = max(1e-12, min_prominence_ratio * vpp)
    dt = float(np.median(np.diff(t)))
    dist_samples = max(1, int(min_distance_s / dt))
    peaks, _ = find_peaks(v_abs, prominence=prom, distance=dist_samples)
    if peaks.size == 0:
        return peaks, 0.0, 0

    # FWHM of the first peak estimated by threshold-crossing at 0.5 × peak height
    i0 = int(peaks[0])
    half = 0.5 * v_abs[i0]
    # search backwards
    left = i0
    while left > 0 and v_abs[left] > half:
        left -= 1
    right = i0
    while right < v_abs.size - 1 and v_abs[right] > half:
        right += 1
    fwhm = float(t[right] - t[left]) if right > left else 0.0
    return peaks, fwhm, int(peaks.size)


# ---------------------------------------------------------- quantities

def pulse_energy(t: np.ndarray, v: np.ndarray, i: np.ndarray) -> TraceResult:
    """E_pulse = (1/N) ∫|V·I| dt over the detected pulse regions."""
    peaks, fwhm, n_pulses = detect_pulses(t, v)
    if n_pulses == 0:
        e_win = float(trapezoid(v * i, t))
        return TraceResult(
            name="Energy per pulse E_pulse",
            value=e_win, unit="J",
            equation_latex=r"E_\mathrm{pulse} = E_\mathrm{window} / N_\mathrm{pulses}",
            substitution_latex=(
                r"N_\mathrm{pulses}=0 \text{ (検出不可、窓全体をパルスとみなす)}\;\;"
                fr"E_\mathrm{{pulse}} \approx {format_si(e_win, 'J')}"
            ),
            steps=["ピーク検出に失敗。窓エネルギーで代用。"],
            sources=["2008_APEX-1-046002"],
        )
    e_win = float(trapezoid(v * i, t))
    e_p = e_win / n_pulses
    return TraceResult(
        name="Energy per pulse E_pulse",
        value=e_p, unit="J",
        equation_latex=r"E_\mathrm{pulse} = \dfrac{E_\mathrm{window}}{N_\mathrm{pulses}}",
        substitution_latex=(
            fr"E_\mathrm{{pulse}} = \dfrac{{{format_si(e_win, 'J')}}}"
            fr"{{{n_pulses}}} = {format_si(e_p, 'J')}"
        ),
        steps=[f"N_pulses = {n_pulses}（prominence 法で検出）",
               f"FWHM (1st pulse) ≈ {fwhm*1e9:.2f} ns"],
        sources=["2008_APEX-1-046002", "2013_CAP-13-1050"],
        extra={"n_pulses": n_pulses, "fwhm": fwhm, "peaks": peaks},
    )


def duty_cycle(t: np.ndarray, v: np.ndarray) -> TraceResult:
    """D = Σ τ_i / T_window (FWHM total / window)."""
    peaks, fwhm, n_pulses = detect_pulses(t, v)
    T = float(t[-1] - t[0])
    if n_pulses == 0 or T <= 0:
        return TraceResult(
            name="Duty cycle D",
            value=float("nan"), unit="(fraction)",
            equation_latex=r"D = \sum\tau_i/T",
        )
    # approx: N_pulses × FWHM（同一パルス幅仮定）
    total_on = n_pulses * fwhm
    D = total_on / T
    return TraceResult(
        name="Duty cycle D",
        value=D, unit="(fraction)",
        equation_latex=r"D = \dfrac{\sum \tau_i}{T_\mathrm{window}}",
        substitution_latex=(
            fr"D \approx \dfrac{{{n_pulses}\times{format_si(fwhm, 's')}}}"
            fr"{{{format_si(T, 's')}}} = {pretty_number(D)}"
        ),
        steps=[f"N_pulses = {n_pulses}, FWHM = {fwhm*1e9:.2f} ns, T = {T*1e6:.2f} μs"],
        sources=["classical pulse-power engineering"],
        extra={"n_pulses": n_pulses, "fwhm": fwhm},
    )


def effective_average_power(v: np.ndarray, i: np.ndarray,
                             duty: float) -> TraceResult:
    """P_eff = P_peak × D. Directly addresses the 1 kW device budget question."""
    p = np.asarray(v, float) * np.asarray(i, float)
    pk_idx = int(np.argmax(np.abs(p)))
    p_peak = float(p[pk_idx])
    p_eff = p_peak * duty
    return TraceResult(
        name="Effective average power (Ppeak·D)",
        value=p_eff, unit="W",
        equation_latex=r"P_\mathrm{eff} = P_\mathrm{peak}\cdot D",
        substitution_latex=(
            fr"P_\mathrm{{eff}} = {format_si(p_peak, 'W')} \times {pretty_number(duty)} "
            fr"= {format_si(p_eff, 'W')}"
        ),
        steps=["ユーザ要望: Peak × Duty で装置全体 1 kW 制約の判定に使用"],
        sources=["lab meeting 2026-04-23"],
    )


def abs_power_mean(t: np.ndarray, v: np.ndarray, i: np.ndarray) -> TraceResult:
    """⟨|P|⟩ = (1/T) ∫ |V·I| dt — captures displacement-current work too."""
    p = np.asarray(v, float) * np.asarray(i, float)
    T = float(t[-1] - t[0])
    val = float(trapezoid(np.abs(p), t) / T) if T > 0 else float("nan")
    return TraceResult(
        name="Absolute instantaneous power time-average ⟨|P|⟩",
        value=val, unit="W",
        equation_latex=r"\langle|P|\rangle = \dfrac{1}{T}\int|V\,I|\,dt",
        substitution_latex=fr"\langle|P|\rangle = {format_si(val, 'W')}",
        steps=["符号を無視した電力の時間平均（誘導/容量性リターンも加算）"],
        sources=["HV-pulse diagnostics literature"],
    )


def crest_factor(v: np.ndarray) -> TraceResult:
    v = np.asarray(v, float)
    v_rms = float(np.sqrt(np.mean(v ** 2)))
    v_peak = float(np.max(np.abs(v)))
    cf = v_peak / v_rms if v_rms > 0 else float("inf")
    return TraceResult(
        name="Crest factor CF (voltage)",
        value=cf, unit="(ratio)",
        equation_latex=r"\mathrm{CF} = V_\mathrm{peak} / V_\mathrm{rms}",
        substitution_latex=(
            fr"\mathrm{{CF}} = {format_si(v_peak, 'V')} / {format_si(v_rms, 'V')} "
            fr"= {pretty_number(cf)}"
        ),
        steps=["正弦波 CF=√2≈1.41、パルス列 CF≈√(1/D)"],
        sources=["classical signal analysis"],
    )


def form_factor(v: np.ndarray) -> TraceResult:
    v = np.asarray(v, float)
    v_rms = float(np.sqrt(np.mean(v ** 2)))
    v_mean_abs = float(np.mean(np.abs(v)))
    ff = v_rms / v_mean_abs if v_mean_abs > 0 else float("inf")
    return TraceResult(
        name="Form factor FF (voltage)",
        value=ff, unit="(ratio)",
        equation_latex=r"\mathrm{FF} = V_\mathrm{rms} / \overline{|V|}",
        substitution_latex=(
            fr"\mathrm{{FF}} = {format_si(v_rms, 'V')} / {format_si(v_mean_abs, 'V')} "
            fr"= {pretty_number(ff)}"
        ),
        steps=["正弦波 FF=π/(2√2)≈1.11、ピーク性が強いほど大"],
        sources=["classical signal analysis"],
    )


def power_density(p_mean_W: float, volume_m3: float) -> TraceResult:
    """p_vol = P̄ / V_plasma (user supplies plasma volume)."""
    if volume_m3 <= 0:
        return TraceResult(
            name="Plasma power density p_vol",
            value=float("nan"), unit="W/m^3",
            equation_latex=r"p_\mathrm{vol} = \bar{P}/V_\mathrm{plasma}",
            steps=["プラズマ体積 V_plasma が未設定"],
        )
    pv = p_mean_W / volume_m3
    return TraceResult(
        name="Plasma power density p_vol",
        value=pv, unit="W/m^3",
        equation_latex=r"p_\mathrm{vol} = \dfrac{\bar{P}}{V_\mathrm{plasma}}",
        substitution_latex=(
            fr"p_\mathrm{{vol}} = \dfrac{{{format_si(p_mean_W, 'W')}}}"
            fr"{{{pretty_number(volume_m3)}\,\text{{m}}^3}} "
            fr"= {pretty_number(pv)}\,\text{{W/m}}^3"
        ),
        steps=[f"V_plasma = {volume_m3:.3e} m^3"],
        sources=["plasma reactor design literature"],
    )
