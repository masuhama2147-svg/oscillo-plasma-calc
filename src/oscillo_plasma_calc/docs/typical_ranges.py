"""Typical-range DB used by the "Error line" anomaly detector.

Ranges are distilled from Nomura-lab paper archive + classical plasma diagnostics
literature. The DB is the single source of truth — UI, CLI, reports all use it.

If a measured quantity lies inside [low, high] → OK.
Inside [low*0.5, low) or (high, high*2]         → NOTICE (edge of typical band).
Outside both                                     → WARNING (suspect).
If extremely far (≤ low*0.1 or ≥ high*10)       → ERROR (likely instrument fault).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TypicalRange:
    key: str
    low: float
    high: float
    unit: str
    below_low_causes: tuple[str, ...] = ()
    above_high_causes: tuple[str, ...] = ()
    references: tuple[str, ...] = ()


_TR: dict[str, TypicalRange] = {}


def _add(tr: TypicalRange) -> None:
    _TR[tr.key] = tr


# Tier 1 ---------------------------------------------------------------

_add(TypicalRange(
    key="vpp", low=3e3, high=1.5e4, unit="V",
    below_low_causes=("電源出力不足", "プローブ分圧比の誤設定",
                      "トリガ失敗で無放電区間のみ取得"),
    above_high_causes=("プローブ入力オーバー", "プローブ飽和 / ダメージ"),
    references=("2013_CAP-13-1050",),
))

_add(TypicalRange(
    key="ipp", low=1.0, high=2e2, unit="A",
    below_low_causes=("放電未点弧（絶縁破壊未達）", "電流プローブ感度不足",
                      "グランド配線のインピーダンス過大"),
    above_high_causes=("電流プローブ飽和", "短絡経路の疑い",
                       "スケール設定誤り（mA→A 誤記）"),
    references=("2011_PSST-20-034016",),
))

_add(TypicalRange(
    key="rise_time", low=1e-9, high=5e-7, unit="s",
    below_low_causes=("Δt が大きすぎて検出下限未達",),
    above_high_causes=("プローブ帯域不足", "パルス整形回路劣化",
                       "検出窓がパルス外"),
    references=("2013_CAP-13-1050",),
))

_add(TypicalRange(
    key="slew_rate_v", low=1e9, high=1e12, unit="V/s",
    below_low_causes=("DC 成分のみ", "プローブ RC 時定数過大"),
    above_high_causes=("ノイズスパイク検出", "接地ループ",),
    references=("2013_CAP-13-1050",),
))

_add(TypicalRange(
    key="slew_rate_i", low=1e8, high=1e11, unit="A/s",
    below_low_causes=("電流プローブ帯域不足",),
    above_high_causes=("ノイズスパイク",),
    references=("2013_CAP-13-1050",),
))

_add(TypicalRange(
    key="peak_power", low=1e3, high=1e6, unit="W",
    below_low_causes=("V と I が直交位相（無効電力支配）",
                       "プローブ接続誤り"),
    above_high_causes=("プローブ飽和", "V/I の誤校正"),
    references=("2006_JJAP-45-8864",),
))

_add(TypicalRange(
    key="energy", low=1e-4, high=1e-1, unit="J",
    below_low_causes=("観測窓内に放電パルス無し",
                       "時間軸単位の誤認識（μs/ns 誤り）"),
    above_high_causes=("時間軸単位の誤認識",
                       "連続波をパルスとして積分してしまっている"),
    references=("2008_APEX-1-046002",),
))

_add(TypicalRange(
    key="mean_power", low=1e1, high=1e3, unit="W",
    below_low_causes=("観測窓が実パルス周期より大幅に長い",),
    above_high_causes=("観測窓が実パルス周期より短い", "単発パルスを連続とみなした"),
    references=("2008_APEX-1-046002",),
))

_add(TypicalRange(
    key="v_rms", low=1e2, high=5e3, unit="V",
    below_low_causes=("デューティ比過小", "ベースライン支配"),
    above_high_causes=("RF 連続波が混入", "デューティ比 >> 50 %"),
    references=(),
))

_add(TypicalRange(
    key="i_rms", low=0.1, high=20.0, unit="A",
    below_low_causes=("放電未点弧",),
    above_high_causes=("連続電流が流れている（DC bias）",),
    references=(),
))


# Tier 2 ---------------------------------------------------------------

_add(TypicalRange(
    key="boltzmann_two_line", low=0.5, high=5.0, unit="eV",
    below_low_causes=("LTE 未成立", "線強度比逆転（自己吸収の疑い）"),
    above_high_causes=("自己吸収無視の誤用", "線ペア選択不良"),
    references=("2006_JJAP-45-8864",),
))

_add(TypicalRange(
    key="excitation_temp_K", low=3e3, high=3e4, unit="K",
    below_low_causes=("線選択の E_u 差が小さく slope 推定誤差大",
                       "強度入力の桁誤り"),
    above_high_causes=("自己吸収", "感度補正未実施"),
    references=("2006_JJAP-45-8864", "2009_JAP-106-113302"),
))

_add(TypicalRange(
    key="stark_ne", low=1e21, high=1e24, unit="m^-3",
    below_low_causes=("Δλ_{1/2} の計測下限未達（分解能不足）",
                       "Stark 係数 α の誤採用"),
    above_high_causes=("Lorentz 成分に Doppler 広がりを混入",
                       "光学的に厚くなっている"),
    references=("2009_POP-16-033503", "Gigosos & Cardeñoso 1996 JPB 29:4795"),
))

_add(TypicalRange(
    key="debye", low=1e-9, high=1e-4, unit="m",
    below_low_causes=("Te, ne の入力値が非物理",),
    above_high_causes=("ne 過小 / Te 過大（入力値再確認）",),
    references=(),
))

_add(TypicalRange(
    key="plasma_freq", low=1e9, high=1e13, unit="Hz",
    below_low_causes=("ne 過小",),
    above_high_causes=("ne 過大",),
    references=("2008_APEX-1-046002",),
))

_add(TypicalRange(
    key="paschen", low=1e2, high=1e5, unit="V",
    below_low_causes=("pd 積が極小点より大幅に小さい", "A, B 誤設定"),
    above_high_causes=("pd 積が大きすぎる", "γ (二次電子放出) 誤設定"),
    references=("2013_CAP-13-1050",),
))


# Tier 3 ---------------------------------------------------------------

_add(TypicalRange(
    key="g_value", low=0.5, high=20.0, unit="molecules/100 eV",
    below_low_causes=("反応器のエネルギー効率悪化",
                       "生成モル数の GC 定量誤差"),
    above_high_causes=("触媒効果 or 測定誤り",
                       "E_abs を過小評価"),
    references=("2012_IJHE-37-16000", "2020_JJIE_99-104"),
))

_add(TypicalRange(
    key="efficiency", low=1.0, high=30.0, unit="%",
    below_low_causes=("反応器設計見直し",
                       "副反応による選択性低下"),
    above_high_causes=("測定再現性要確認", "ΔH 誤設定"),
    references=("2017_JEPE-10-335",),
))


# Advanced electrical -----------------------------------------------

_add(TypicalRange(
    key="pulse_energy", low=1e-6, high=1e-2, unit="J",
    below_low_causes=("パルス検出失敗", "放電未点弧"),
    above_high_causes=("窓内のパルス数 N 過小評価", "観測窓短すぎ"),
    references=("2013_CAP-13-1050",),
))
_add(TypicalRange(
    key="duty_cycle", low=1e-4, high=0.3, unit="(fraction)",
    below_low_causes=("FWHM 検出失敗",),
    above_high_causes=("ほぼ連続波", "観測窓がパルス幅と同じ"),
    references=(),
))
_add(TypicalRange(
    key="effective_average_power", low=1.0, high=1000.0, unit="W",
    below_low_causes=("デューティ比過小", "ピーク検出失敗"),
    above_high_causes=("装置予算 1 kW 超過の恐れ", "PRF 設定過大"),
    references=("lab meeting 2026-04-23",),
))
_add(TypicalRange(
    key="abs_power_mean", low=10.0, high=5000.0, unit="W",
    below_low_causes=(), above_high_causes=("観測窓 ≠ 1 周期",),
    references=(),
))
_add(TypicalRange(
    key="crest_factor", low=1.0, high=30.0, unit="(ratio)",
    below_low_causes=("連続波 or 強く平坦化した波形",),
    above_high_causes=("単発スパイク", "トリガ誤検出"),
    references=(),
))
_add(TypicalRange(
    key="form_factor", low=1.0, high=5.0, unit="(ratio)",
    below_low_causes=(), above_high_causes=("極端なピーク性波形",),
    references=(),
))
_add(TypicalRange(
    key="power_density", low=1e8, high=1e12, unit="W/m^3",
    below_low_causes=("プラズマ体積過大入力",),
    above_high_causes=("プラズマ体積過小", "実際はストリーマ近傍の局所値"),
    references=("Bruggeman 2016 PSST 25:053002",),
))

# Oil synthesis KPIs ------------------------------------------------

_add(TypicalRange(
    key="sei", low=100.0, high=2000.0, unit="kJ/mol",
    below_low_causes=("n_CO2 過大入力", "E_plasma 過小"),
    above_high_causes=("SEI 過大 → η_SE 低下", "供給 CO₂ 流量過小"),
    references=("Snoeckx & Bogaerts 2017 CSR 46:5805",),
))
_add(TypicalRange(
    key="energy_cost", low=200.0, high=5000.0, unit="kJ/mol",
    below_low_causes=("触媒併用の高効率反応",),
    above_high_causes=("選択性低下", "反応器設計見直し"),
    references=("Bogaerts & Neyts 2018 ACS Energy Lett",),
))
_add(TypicalRange(
    key="chi_co2", low=0.5, high=30.0, unit="%",
    below_low_causes=("SEI 不足", "反応時間短い"),
    above_high_causes=("触媒併用 or 再循環", "GC 定量誤差"),
    references=("Snoeckx & Bogaerts 2017",),
))
_add(TypicalRange(
    key="eta_se", low=2.0, high=40.0, unit="%",
    below_low_causes=("SEI 過大", "χ 過小"),
    above_high_causes=("測定誤差 or 触媒併用を超えるメカニズム",),
    references=(),
))
_add(TypicalRange(
    key="asf", low=0.3, high=0.99, unit="(fraction)",
    below_low_causes=("軽質化", "炭素 C2+ 生成低"),
    above_high_causes=("重質化 (wax 域)",),
    references=("Anderson 1984",),
))

# Non-equilibrium ---------------------------------------------------

_add(TypicalRange(
    key="e_over_n", low=5.0, high=1000.0, unit="Td",
    below_low_causes=("電場入力過小", "高圧ガス密度"),
    above_high_causes=("アーク化の可能性", "電場入力過大"),
    references=("Phelps LXCat",),
))
_add(TypicalRange(
    key="mean_e_energy", low=0.5, high=20.0, unit="eV",
    below_low_causes=("E/N 小 → EEDF 裾不足",),
    above_high_causes=("E/N 過大",),
    references=("Fridman 2008",),
))
_add(TypicalRange(
    key="tv_rot_ratio", low=1.0, high=100.0, unit="(ratio)",
    below_low_causes=("熱平衡に近い",),
    above_high_causes=("強非平衡",),
    references=("Fridman 2008",),
))
_add(TypicalRange(
    key="t_vib", low=1000.0, high=8000.0, unit="K",
    below_low_causes=("強度比 I_h/I_l 不正",),
    above_high_causes=("自己吸収 or 逆転分布",),
    references=("Bruggeman 2014 PSST",),
))

# Operational -------------------------------------------------------

_add(TypicalRange(
    key="budget_margin", low=0.0, high=100.0, unit="%",
    below_low_causes=("予算超過（運用停止を検討）",),
    above_high_causes=(),
    references=("lab meeting 2026-04-23",),
))
_add(TypicalRange(
    key="eta_device", low=30.0, high=95.0, unit="%",
    below_low_causes=("電源効率低下", "待機電力が装置全体の大部分を占める"),
    above_high_causes=("W_socket 入力誤り",),
    references=("lab meeting 2026-04-23",),
))


TYPICAL_RANGES: dict[str, TypicalRange] = dict(_TR)


def get_range(key: str) -> TypicalRange | None:
    return TYPICAL_RANGES.get(key)
