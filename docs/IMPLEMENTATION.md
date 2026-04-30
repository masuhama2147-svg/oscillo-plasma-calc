# 実装内容 完全リファレンス

野村研究室 液中プラズマ オシロスコープ波形 & 発光分光 解析ソフトの **すべての実装** を 1 ファイルにまとめた技術資料。研究者が将来コードを保守・拡張する際の 1 次資料として書いている。

ソースコード総量: 約 **5,281 行**（src/ + tests/、Python）

---

## 目次

1. [システム全体像](#1-システム全体像)
2. [モジュール構成](#2-モジュール構成)
3. [データフロー](#3-データフロー)
4. [Tier 1 — 電気系の実装](#4-tier-1--電気系の実装)
5. [Tier 2 — プラズマ診断の実装](#5-tier-2--プラズマ診断の実装)
6. [Tier 3 — 化学・油合成 KPI の実装](#6-tier-3--化学油合成-kpi-の実装)
7. [励起温度モジュール（n 本線 Boltzmann plot）](#7-励起温度モジュール)
8. [信号処理・前処理](#8-信号処理前処理)
9. [品質保証（QA）](#9-品質保証qa)
10. [Shiny UI 実装](#10-shiny-ui-実装)
11. [テスト](#11-テスト)
12. [文書化レイヤ](#12-文書化レイヤ)
13. [全実装ファイル一覧](#13-全実装ファイル一覧)

---

## 1. システム全体像

### 1.1 提供する機能

| カテゴリ | 提供物 |
|---|---|
| 入力 | xlsx / CSV のオシロスコープ波形、発光分光強度 CSV |
| 計算 | 電気系 12+ 量、プラズマ診断 12+ 量、化学 KPI 8 量、励起温度 |
| 検証 | CSV バリデータ、計算結果の異常検出（エラーライン） |
| 出力 | 数値、波形プロット、Markdown レポート、3 段階解説（初学者/研究者/博士） |
| UI | Shiny for Python、KaTeX 数式レンダリング、カテゴリ分けトレース |

### 1.2 設計思想

1. **すべての計算が `TraceResult` を返す** — 値・単位・LaTeX 式・数値代入・中間ステップ・根拠論文を 1 つの dataclass で持つ
2. **離散化はライブラリ任せ** — 自前実装を最小化（scipy.integrate / scipy.signal / scipy.fft）
3. **理論式は sympy で一元定義** — `symbolic/equations.py` に登録、UI と PDF で同じ LaTeX を共有
4. **異常検出は閾値表で定義** — `docs/typical_ranges.py` の 1 ファイルが正解の出典
5. **解説テキストは 3 レベル管理** — `docs/explanations.py` で初学者・研究者・博士の 3 段を持つ

---

## 2. モジュール構成

```
src/oscillo_plasma_calc/
├── __init__.py
├── config/                 # 物理定数、デフォルトパラメータ
│   ├── constants.py        # ε₀, k_B, e, m_e, c, h, N_A …
│   └── defaults.yaml       # Paschen A,B,γ や標準ギャップ等
├── io_layer/               # データ I/O
│   ├── schema.py           # Waveform dataclass（time, voltage, current）
│   ├── xlsx_loader.py      # 既存 xlsx → Waveform
│   └── csv_loader.py       # CSV ↔ Waveform、メタデータ key=value 対応
├── signal/                 # 信号処理（前処理・FFT・ピーク検出）
│   ├── filtering.py        # 移動平均 / Savitzky-Golay
│   ├── peaks.py            # Vpp/Ipp/立ち上がり/スルーレート
│   ├── fft.py              # rFFT + Hanning 窓
│   └── preprocess.py       # DC オフセット補正・zero-crossing 同期
├── electrical/             # 電気系計算
│   ├── instant_power.py    # P(t), Ppeak
│   ├── energy_integral.py  # E = ∫ V·I dt, P̄ = E/T
│   ├── rms.py              # Vrms / Irms
│   ├── lissajous.py        # Manley 法（V-q ループ面積）
│   ├── impedance.py        # Z(t) = V/I（ガード閾値あり）
│   └── advanced.py         # ★ パルス検出, E_pulse, Duty, P_eff,
│                           #    ⟨|P|⟩, Crest/Form factor, power density
├── plasma/                 # プラズマ診断
│   ├── boltzmann.py        # 2 本線 法による Te
│   ├── stark.py            # Stark 広がりによる ne
│   ├── debye.py            # Debye 長 + プラズマ周波数
│   ├── ohmic.py            # σE² Ohmic 加熱密度
│   ├── paschen.py          # Paschen 破壊電圧
│   └── nonequilibrium.py   # ★ 換算電場 E/N, 電子平均エネルギー,
│                           #    非平衡度 Te/Tgas, 振動温度 Tv
├── chemistry/              # 化学・反応評価
│   ├── g_value.py          # G 値（100 eV あたり生成分子数）
│   ├── efficiency.py       # 化学エネルギー変換効率 η
│   ├── selectivity.py      # 生成物選択性 X_k
│   └── oil_synthesis.py    # ★ SEI, EC, χ_CO2, η_SE, ASF α
├── spectroscopy/           # n 本線 Boltzmann plot
│   ├── lines.py            # 5 元素 × 24 本のスペクトル線 DB
│   ├── boltzmann_plot.py   # LSM フィット + R² LTE 直線性
│   └── csv_loader.py       # 強度 CSV 入力
├── qa/                     # 品質保証
│   ├── csv_validator.py    # アップロード CSV のバリデーション
│   ├── anomaly.py          # 計算結果のエラーライン判定
│   └── operational.py      # ★ 装置 1 kW 予算、η_dev、Q_cool
├── symbolic/
│   └── equations.py        # 全 18 理論式を sympy で一元定義
├── docs/                   # 解説テキスト・閾値 DB
│   ├── explanations.py     # 物理量 × 3 レベル解説（初学者/研究者/博士）
│   └── typical_ranges.py   # 各量の典型範囲 + 範囲外原因 + 根拠論文
├── report/                 # レポート出力
│   ├── trace.py            # TraceResult dataclass
│   ├── markdown.py         # Markdown レポート生成
│   └── ui_format.py        # format_si / pretty_number ヘルパ
├── pipeline.py             # Waveform → AnalysisBundle（自動連結）
└── ui/
    └── app.py              # Shiny for Python アプリ（9 タブ）

★ = 今回新規実装（advanced / nonequilibrium / oil_synthesis / operational）
```

---

## 3. データフロー

```
┌────────────────────────────────────────────────────────────────────┐
│                          ユーザー入力                                │
│  ┌───────────────┐  ┌───────────────┐  ┌─────────────────┐       │
│  │  xlsx 既存    │  │  CSV 自前     │  │ 発光分光 強度   │       │
│  └───────┬───────┘  └───────┬───────┘  └────────┬────────┘       │
└──────────┼──────────────────┼────────────────────┼──────────────────┘
           ▼                  ▼                    ▼
    ┌───────────────────────────────┐    ┌────────────────────────┐
    │  io_layer.{xlsx_loader,        │    │ spectroscopy.csv_loader│
    │             csv_loader}        │    └─────────┬──────────────┘
    └───────────────┬───────────────┘              │
                    ▼                              │
    ┌───────────────────────────────┐              │
    │   qa.csv_validator            │              │
    │  （列・Δt・オフセット・桁）  │              │
    └───────────────┬───────────────┘              │
                    ▼                              │
    ┌───────────────────────────────┐              │
    │   signal.preprocess           │              │
    │   （DC offset, zero-crossing） │              │
    └───────────────┬───────────────┘              │
                    ▼                              │
            ┌───────Waveform───────┐               │
            └───────────┬──────────┘               │
                        ▼                          │
    ┌────────────────────────────────────┐         │
    │  pipeline.analyze_electrical       │         │
    │  ・ Tier 1: signal.peaks /         │         │
    │    electrical.{...}                │         │
    │  ・ Tier 1+: electrical.advanced   │         │
    │  ・ qa.operational.budget          │         │
    │  ・ qa.anomaly.classify (auto)     │         │
    │  ・ docs.explanations bind         │         │
    └───────────────┬────────────────────┘         │
                    ▼                              │
       ┌──── AnalysisBundle ────┐                  │
       └────────────┬───────────┘                  │
                    │                              │
       ┌────────────┼──────────────┐               ▼
       ▼            ▼              ▼      ┌────────────────────┐
    Markdown      Shiny UI     plot         │ spectroscopy.        │
    report.markdown          plotly         │  excitation_         │
                                            │  temperature         │
                                            │  + R² LTE check      │
                                            └──────────────────────┘

    Tier 2/3 はユーザーが UI で発光分光・GC 入力 → plasma / chemistry へ流入。
```

---

## 4. Tier 1 — 電気系の実装

電気系はオシロの V(t), I(t) **だけで** 計算できる物理量群。pipeline で自動連結される。

### 4.1 Vpp / Ipp（ピーク間電圧・電流）

| 項目 | 内容 |
|---|---|
| 実装 | `signal/peaks.py:detect_vpp / detect_ipp` |
| 式 | $V_{pp} = V_{\max} - V_{\min}$ |
| アルゴリズム | `np.max(v) - np.min(v)` |
| 単位 | V / A |
| 異常閾値 | Vpp 3〜15 kV、Ipp 1〜200 A（[`typical_ranges.py`](../src/oscillo_plasma_calc/docs/typical_ranges.py)） |
| 根拠論文 | 2013_CAP-13-1050、2011_PSST-20-034016 |

### 4.2 立ち上がり時間 t_r

| 項目 | 内容 |
|---|---|
| 実装 | `signal/peaks.py:rise_time` |
| 式 | $t_r = t(x = 0.9 x_{\max}) - t(x = 0.1 x_{\max})$ |
| アルゴリズム | `np.argmax(x >= threshold)` で閾値交差時刻を 2 点取得 |
| 単位 | s |
| 異常閾値 | 1 ns〜500 ns（ns パルス前提） |

### 4.3 dV/dt, dI/dt（スルーレート）

| 項目 | 内容 |
|---|---|
| 実装 | `signal/peaks.py:slew_rate` |
| 式 | $\left.\frac{dV}{dt}\right|_{\max} = \max_k \left|\frac{V_{k+1} - V_{k-1}}{2\Delta t}\right|$ |
| アルゴリズム | `np.gradient(x) / np.gradient(t)` で中央差分（O(Δt²)）→ 絶対値最大 |
| 異常閾値 | dV/dt 10⁹〜10¹² V/s、dI/dt 10⁸〜10¹¹ A/s |

### 4.4 P(t) 瞬時電力

| 項目 | 内容 |
|---|---|
| 実装 | `electrical/instant_power.py:instantaneous_power` |
| 式 | $P(t) = V(t) \cdot I(t)$ |
| アルゴリズム | numpy 要素積 |
| 出力 | 配列（時系列） |

### 4.5 ピーク電力 P_peak

| 項目 | 内容 |
|---|---|
| 実装 | `electrical/instant_power.py:peak_power` |
| 式 | $P_\text{peak} = \max_k |V_k I_k|$ |
| 異常閾値 | 1 kW〜1 MW |

### 4.6 吸収エネルギー E

| 項目 | 内容 |
|---|---|
| 実装 | `electrical/energy_integral.py:absorbed_energy` |
| 式 | $E = \int_{t_0}^{t_N} V(t)\,I(t)\,dt$ |
| 離散化 | 合成台形則（`scipy.integrate.trapezoid`、誤差 O(Δt²)） |
| 累積版 | `cumulative_trapezoid` で E(t) も同時に保持 |
| 異常閾値 | 0.1 mJ〜100 mJ |

### 4.7 平均電力 P̄

| 項目 | 内容 |
|---|---|
| 実装 | `electrical/energy_integral.py:mean_power` |
| 式 | $\bar{P} = E / T$ |
| 注意 | T は **観測窓** の長さ。実 PRF とは別 |

### 4.8 Vrms / Irms

| 項目 | 内容 |
|---|---|
| 実装 | `electrical/rms.py:v_rms / i_rms` |
| 式 | $V_\mathrm{rms} = \sqrt{(1/T) \int V^2 dt}$ |
| 離散化 | 被積分関数 V² → 台形積分 → /T → √ |
| 検証 | 正弦波で Vrms = V_0/√2 が成立（`test_electrical.py:test_rms_half_sqrt2`） |

### 4.9 Lissajous (V-q) 平均電力（Manley 法）

| 項目 | 内容 |
|---|---|
| 実装 | `electrical/lissajous.py:lissajous_power` |
| 式 | $\bar{P} = f \oint V\,dq$、$q(t) = \int I(t)\,dt$ |
| アルゴリズム | (1) `cumulative_trapezoid(I, t)` で q 取得 (2) Shoelace 公式で V-q 多角形面積 (3) f 倍 |
| 注意 | モニタ Cm 無しの簡易版。厳密 Manley 法ではない（Peeters 2015 補正は将来課題） |
| 根拠 | Manley 1943、Peeters & van der Laan 2015 PSST 24:015014 |

### 4.10 瞬時インピーダンス Z(t)

| 項目 | 内容 |
|---|---|
| 実装 | `electrical/impedance.py:instant_impedance` |
| 式 | $Z(t) = V(t) / I(t)$ |
| ガード | `|I| < 1 mA` の領域は NaN（ゼロ割防止） |

### 4.11 FFT パワースペクトル

| 項目 | 内容 |
|---|---|
| 実装 | `signal/fft.py:power_spectrum / dominant_frequency` |
| アルゴリズム | (1) `x * np.hanning(n)` で窓掛け (2) `scipy.fft.rfft` (3) 振幅 = `2/n × |X|` |
| Nyquist | f_s/2、Δt=2 ns なら 250 MHz 上限 |

### 4.12 ★ パルス検出 + E_pulse + Duty cycle（新規）

| 項目 | 内容 |
|---|---|
| 実装 | `electrical/advanced.py:detect_pulses, pulse_energy, duty_cycle` |
| アルゴリズム | `scipy.signal.find_peaks(|v|, prominence=0.5·Vpp, distance=100ns)` で N 検出、最初のパルスから FWHM を `peak_widths` で取得 |
| 派生量 | $E_\text{pulse} = E_\text{window}/N$、$D = N \cdot \text{FWHM}/T$ |
| チューニング | 液中 ns パルス向けに prominence と distance を調整。サブ振動を 1 パルスに丸める |
| 検証 | `test_advanced_electrical.py:test_detect_pulses_counts_4`（合成 Gaussian 4 パルス） |

### 4.13 ★ P_eff = Ppeak × D（実効平均電力、装置 1 kW 制約）

| 項目 | 内容 |
|---|---|
| 実装 | `electrical/advanced.py:effective_average_power` |
| 式 | $P_\text{eff} = P_\text{peak} \cdot D$ |
| 用途 | 会議要件「装置全体 1 kW 以下」を瞬時値（kW オーダー）と Duty で安全側に判定 |
| 出力 | W |
| 異常閾値 | 1〜1000 W、超過で error |

### 4.14 ★ ⟨|P|⟩ 絶対値時間平均

| 項目 | 内容 |
|---|---|
| 実装 | `electrical/advanced.py:abs_power_mean` |
| 式 | $\langle|P|\rangle = (1/T) \int |V \cdot I|\,dt$ |
| 用途 | 誘導/容量リターンも「仕事」として数えた実効値。⟨|P|⟩/P̄ 比でリアクタンス成分の支配度を判定 |

### 4.15 ★ Crest factor / Form factor

| 項目 | 内容 |
|---|---|
| 実装 | `electrical/advanced.py:crest_factor, form_factor` |
| 式 | CF = $V_\text{peak}/V_\text{rms}$、FF = $V_\text{rms}/\langle|V|\rangle$ |
| 検証 | 正弦波で CF=√2、FF=π/(2√2)（`test_advanced_electrical.py`） |

### 4.16 ★ プラズマ電力密度 p_vol

| 項目 | 内容 |
|---|---|
| 実装 | `electrical/advanced.py:power_density` |
| 式 | $p_\text{vol} = \bar{P}/V_\text{plasma}$ |
| 入力 | プラズマ体積（電極ギャップ × 断面積、ユーザー入力） |
| 異常閾値 | 10⁸〜10¹² W/m³（液中ストリーマ典型） |

---

## 5. Tier 2 — プラズマ診断の実装

ユーザーが発光分光（OES）データを別途入力すると Tier 2 が動く。

### 5.1 Boltzmann 2 本線法による電子温度 Te

| 項目 | 内容 |
|---|---|
| 実装 | `plasma/boltzmann.py:electron_temperature_boltzmann` |
| 式 | $\frac{I_{ij}}{I_{kl}} = \frac{g_i A_{ij} \nu_{ij}}{g_k A_{kl} \nu_{kl}} \exp\!\left[-\frac{E_i - E_k}{k_B T_e}\right]$ |
| 解 | $T_e = -\dfrac{E_i - E_k}{k_B \ln\!\left(\frac{I_{ij}/I_{kl}}{\text{prefactor}}\right)}$ |
| 入出力 | 入力: 線対の I, g, A, ν, E（10 引数）／出力: T_e [eV] |
| 検証 | T_e = 1 eV を逆算で復元（`test_plasma.py:test_boltzmann_round_trip`） |
| 根拠 | 2006_JJAP-45-8864、2009_JAP-106-113302 |

### 5.2 Stark 広がりによる ne

| 項目 | 内容 |
|---|---|
| 実装 | `plasma/stark.py:electron_density_stark` |
| 式 | $n_e = \alpha(T_e) \cdot (\Delta\lambda_{1/2})^{3/2}$ |
| 既定 α | 1.0×10²³ m⁻³·nm⁻¹·⁵（液中大気圧水プラズマ典型） |
| 根拠 | 2009_POP-16-033503、Gigosos & Cardeñoso 1996 JPB 29:4795 |

### 5.3 Debye 長 / プラズマ周波数

| 項目 | 内容 |
|---|---|
| 実装 | `plasma/debye.py:debye_length, plasma_frequency` |
| 式 | $\lambda_D = \sqrt{\varepsilon_0 k_B T_e/(n_e e^2)}$、$f_p = (1/2\pi)\sqrt{n_e e^2/(m_e \varepsilon_0)}$ |
| Te 単位変換 | 入力 eV、内部で K に変換（`Te_K = Te_eV * e / k_B`） |
| 検証 | T_e=1 eV, n_e=10¹⁸ で λ_D 1e-7〜1e-4 m、f_p 1〜100 GHz オーダー |

### 5.4 Ohmic 加熱密度

| 項目 | 内容 |
|---|---|
| 実装 | `plasma/ohmic.py:ohmic_heating_density` |
| 式 | $p_\text{ohm} = \sigma E^2$ |
| 用途 | 液中 Joule 加熱の体積密度。気泡形成の駆動力評価 |

### 5.5 Paschen 破壊電圧

| 項目 | 内容 |
|---|---|
| 実装 | `plasma/paschen.py:paschen_breakdown_voltage` |
| 式 | $V_b = \frac{B p d}{\ln(A p d) - \ln \ln(1 + 1/\gamma)}$ |
| 既定 | A=112.5 (Pa·m)⁻¹、B=2737.5 V/(Pa·m)、γ=0.01（空気） |
| 注意 | 液中には厳密には不適用、「気相参照値」として表示 |

### 5.6 ★ 換算電場 E/N（Townsend 単位）

| 項目 | 内容 |
|---|---|
| 実装 | `plasma/nonequilibrium.py:reduced_electric_field` |
| 式 | $E/N = E/n_\text{gas}$ [V·m²]、Td 換算で 10²¹ 倍 |
| n_gas | 入力圧力 + 温度から ideal gas: $n = p/(k_B T)$ |
| 単位 | Td (Townsend, 1 Td = 10⁻²¹ V·m²) |
| 異常閾値 | 5〜1000 Td |
| 根拠 | Phelps LXCat、Fridman 2008 |

### 5.7 ★ 電子平均エネルギー ⟨ε⟩

| 項目 | 内容 |
|---|---|
| 実装 | `plasma/nonequilibrium.py:mean_electron_energy` |
| 経験式 | $\langle\varepsilon\rangle \approx 0.02 \cdot (E/N)$ [eV/Td]（粗近似） |
| 厳密化 | BOLSIG+ の数値表参照が将来の課題 |

### 5.8 ★ 非平衡度 T_e/T_gas

| 項目 | 内容 |
|---|---|
| 実装 | `plasma/nonequilibrium.py:non_equilibrium_ratio` |
| 用途 | > 30 で非熱的 CO₂ 還元に有利 |

### 5.9 ★ 振動温度 T_vib

| 項目 | 内容 |
|---|---|
| 実装 | `plasma/nonequilibrium.py:vibrational_temperature_from_ratio` |
| 式 | 2 振動準位の強度比から逆算: $\frac{I_{v_2}}{I_{v_1}} = \exp\!\left[-\Delta E_\text{vib}/(k_B T_\text{vib})\right]$ |
| 用途 | CO₂ ladder climbing 効率の指標。3000-6000 K が最効率域 |

---

## 6. Tier 3 — 化学・油合成 KPI の実装

GC 分析データを入力した時に動く。油合成研究（CO₂ 還元 → 液体燃料）固有の KPI を博士レベルで実装。

### 6.1 G 値（基本）

| 項目 | 内容 |
|---|---|
| 実装 | `chemistry/g_value.py:g_value` |
| 式 | $G = N_\text{prod} / (E_\text{abs}/100\,\text{eV})$ |
| 単位変換 | E_abs [J] → eV: × 6.241×10¹⁸ |

### 6.2 化学効率 η

| 項目 | 内容 |
|---|---|
| 実装 | `chemistry/efficiency.py:chemical_efficiency` |
| 式 | $\eta_\text{chem} = (\Delta H \cdot n_\text{prod})/E_\text{plasma} \times 100\%$ |

### 6.3 選択性 X

| 項目 | 内容 |
|---|---|
| 実装 | `chemistry/selectivity.py:selectivity` |
| 式 | $X_k = n_k / \sum_j n_j$ |

### 6.4 ★ SEI（比エネルギー投入量）

| 項目 | 内容 |
|---|---|
| 実装 | `chemistry/oil_synthesis.py:specific_energy_input` |
| 式 | $\text{SEI} = E_\text{plasma} / n_\text{CO2}$ |
| 単位 | kJ/mol |
| 異常閾値 | 100〜2000 kJ/mol（CO₂ プラズマ標準値） |
| 根拠 | Snoeckx & Bogaerts 2017 ChemSocRev 46:5805 |

### 6.5 ★ エネルギーコスト EC

| 項目 | 内容 |
|---|---|
| 実装 | `chemistry/oil_synthesis.py:energy_cost` |
| 式 | $\text{EC} = E_\text{plasma} / n_\text{prod}$ |
| 異常閾値 | 200〜5000 kJ/mol（メタノール合成標準） |

### 6.6 ★ CO₂ 変換率 χ

| 項目 | 内容 |
|---|---|
| 実装 | `chemistry/oil_synthesis.py:co2_conversion_rate` |
| 式 | $\chi = (n_\text{in} - n_\text{out})/n_\text{in} \times 100\%$ |
| 異常閾値 | 0.5〜30 %（液中プラズマ典型） |

### 6.7 ★ 単位エネルギー変換効率 η_SE

| 項目 | 内容 |
|---|---|
| 実装 | `chemistry/oil_synthesis.py:single_pass_energy_efficiency` |
| 式 | $\eta_\text{SE} = (\chi \cdot \Delta H_r)/\text{SEI}$ |
| 異常閾値 | 2〜40 % |

### 6.8 ★ ASF 連鎖成長確率 α

| 項目 | 内容 |
|---|---|
| 実装 | `chemistry/oil_synthesis.py:asf_chain_probability` |
| 理論 | Anderson-Schulz-Flory 分布: $W_n = n(1-\alpha)^2 \alpha^{n-1}$ |
| アルゴリズム | $\ln(W_n/n)$ vs n を 1 次回帰 → slope = ln(α) → α = exp(slope) |
| 解釈 | α=0.7-0.95 が FT 典型、α>0.95 でワックス（重油）域 |
| 検証 | $W_n = n \alpha^n$ の合成データから α=0.85 を 5e-3 精度で復元 |

---

## 7. 励起温度モジュール

`励起温度計算シート ver.2.xlsx` を完全 CSV 自動化。野村研で 20 年使われている n 本線 Boltzmann plot を実装。

### 7.1 スペクトル線データベース

| 元素 | 本数 | 波長範囲 | 実装 |
|---|---|---|---|
| H | 3 (Hα/Hβ/Hγ) | 434–656 nm | `spectroscopy/lines.py` |
| O | 6 (777, 844 nm 群) | 777–845 nm | 同上 |
| W | 5 (5d-6p 系列) | 321–429 nm | 同上 |
| Al | 5 (3p, 4s, 3d) | 308–669 nm | 同上 |
| Cu | 5 (4p, 4d) | 324–521 nm | 同上 |

各線は λ, E_u, E_l, g, A の NIST 値を保持。

### 7.2 アルゴリズム

```python
# spectroscopy/boltzmann_plot.py:excitation_temperature
y_i = ln(I_i / (g_i · A_i · ν_i))     # ν = c/λ
x_i = E_u_i - E_l_i                    # xlsx と同じ
# 最小二乗法
m = (n·Σxy - Σx·Σy) / (n·Σxx - (Σx)²)
T_e = -1 / (k_B · m)                   # k_B = 8.617e-5 eV/K
# 直線性 R²
R² = (n·Σxy - Σx·Σy)² / [(n·Σxx - (Σx)²)(n·Σyy - (Σy)²)]
```

### 7.3 LTE 直線性判定

`BoltzmannPlotResult.lte_quality_label`:
- R² ≥ 0.95: 「LTE 直線性 良好」
- R² ≥ 0.85: 「LTE 直線性 やや弱い」
- R² < 0.85: 「LTE 非成立の疑い」
- n < 3: 「指標不足 (n<3)」

会議 2026-04-23 で野村先生が指示した「LTE を実測で確認」要件への直接の応答。

### 7.4 検証

5 元素（H/O/W/Al/Cu）で xlsx の手計算と数値完全一致を `test_spectroscopy.py` で固定。
- H: T_e = 10,800 K
- O: 3,999 K
- W: 7,989 K
- Al: 7,409 K
- Cu①: 662 K（線対の E_u 差小により低温、検出可能な「弱点」として保持）

---

## 8. 信号処理・前処理

### 8.1 DC オフセット補正

| 項目 | 内容 |
|---|---|
| 実装 | `signal/preprocess.py:remove_dc_offset` |
| アルゴリズム | 先頭 2% サンプルの平均を全体から引く（pre-trigger 領域を 0 V とみなす） |
| 用途 | プローブのベースラインドリフト補正 |

### 8.2 立ち上がりエッジ同期

| 項目 | 内容 |
|---|---|
| 実装 | `signal/preprocess.py:align_to_first_rising_edge` |
| アルゴリズム | 最大値の 10% を最初に超える index を t=0 にシフト |

### 8.3 統合エントリポイント

| 項目 | 内容 |
|---|---|
| 実装 | `signal/preprocess.py:preprocess` |
| 引数 | `remove_offset=True, align_edge=False`（個別 ON/OFF 可能） |
| Shiny UI | Upload タブのチェックボックスで切替可能 |

### 8.4 フィルタリング

`signal/filtering.py` に `moving_average` と `savgol_smooth` を用意。現状は UI から呼び出していないが、将来のスムージング前処理用に確保。

---

## 9. 品質保証（QA）

### 9.1 CSV バリデータ

| 項目 | 内容 |
|---|---|
| 実装 | `qa/csv_validator.py:validate_csv` |
| チェック項目 | (1) ファイル存在 (2) パース可能性 (3) 必須列 `time_s, voltage_V, current_A` (4) 行数 ≥ 10 (5) NaN なし (6) 時間軸の単調性 (7) Δt の CV ≤ 5% (8) DC オフセットの大きさ (9) 桁オーダーの妥当性 (10) 全ゼロでない |
| 出力 | `ValidationReport` に `hard_errors`, `warnings`, `notices`, `ok_items` を分類 |
| UI 連携 | Upload タブで色分けバナー表示。hard_error 1 件でも計算停止 |

### 9.2 異常検出（エラーライン）

| 項目 | 内容 |
|---|---|
| 実装 | `qa/anomaly.py:classify(key, value)` |
| 閾値 DB | `docs/typical_ranges.py` の `TYPICAL_RANGES` 辞書 |
| 4 段階判定 | error: 1/10× 以下 or 10× 以上、warning: 範囲外、notice: 端寄り (lower 15% / upper 85%) [対数スケール]、ok: 中央 |
| 自動付与 | `pipeline._bind` が compute 関数の戻りに `anomaly` 属性を付加 |

### 9.3 装置運用チェック（1 kW 予算）

| 項目 | 内容 |
|---|---|
| 実装 | `qa/operational.py:device_power_budget, device_efficiency, heat_dissipation_requirement` |
| 1 kW 予算 | M = (W_budget − P_est) / W_budget × 100 % |
| 警告レベル | M < 0 → error、M < 10% → warning、M ≥ 30% → ok |
| η_dev | P̄_plasma / W_socket（コンセント側比較） |
| 出典 | 会議 2026-04-23 |

---

## 10. Shiny UI 実装

### 10.1 タブ構成（9 タブ）

| # | タブ | 機能 |
|---|---|---|
| 1 | Upload | xlsx/CSV 入力、3 STEP（仕様 → アップロード → 結果）、バリデーション、DC offset 切替、socket_power 比較 |
| 2 | Waveform | V(t)/I(t) plotly 双軸 |
| 3 | Electrical | サマリ表 + P(t) + Lissajous + コンセント比較 |
| 4 | FFT | 両対数 power spectrum |
| 5 | Plasma | Boltzmann 2 本線 / Stark / Debye / Ohmic / Paschen の入力欄 |
| 6 | Chemistry | GC データから G 値・η・SEI |
| 7 | 励起温度 Te | n 本線 Boltzmann plot + R² 表示、CSV アップロード対応 |
| 8 | Trace | コンパクトカード（カテゴリ分け、フィルタ、stat header） |
| 9 | Export | Markdown / CSV ダウンロード |

各タブ上部に「▼ このタブの読み方」折りたたみガイドが常設。

### 10.2 Trace タブ アーキテクチャ

```
┌── 📊 解析サマリ（sticky position）──────────┐
│ 計算済 N | ✓正常 / ℹ注意 / ⚠警告 / ✗異常    │
│ 🔌 装置予算チェック バナー                  │
└──────────────────────────────────────────────┘

┌── フィルタ + 展開コントロール ──────────────┐
│ [全部] [警告のみ] [異常のみ] [全部開く]    │ ← クライアント側 JS
└──────────────────────────────────────────────┘

━━━ ⚡ 電気系 (12) ━━━━━━━━━━━━━━━━━━━━ ▾
  ▶ Card 1（深刻度順、内部 details で折りたたみ）
    ▾ 🔰 初学者向け
    ▷ 🔬 研究者向け
    ▷ 🎓 博士向け
    ▷ 📐 理論式・数値代入
    ┌── ⚠ エラーライン ───┐
    │ 可能性のある原因…  │
    │ 参考論文: 2013_…    │
    └─────────────────────┘
━━━ 🌡️ プラズマ診断 (n) ━━━━━━━━━━━━━━━ ▾
━━━ 🧪 油合成 KPI (n) ━━━━━━━━━━━━━━━━━ ▾
━━━ 🔌 装置運用 (n) ━━━━━━━━━━━━━━━━━━ ▾
```

### 10.3 数式レンダリング

| 項目 | 内容 |
|---|---|
| 採用 | KaTeX 0.16.11 + auto-render + MutationObserver |
| 経緯 | MathJax 試行で `innerHTML` 経由の `<script>` が実行されない HTML5 仕様の落とし穴に当たり、根本対策で KaTeX へ移行 |
| 実装 | `ui/app.py:MATH_HEADER` に CSS / JS / auto-render / boot script を集約 |
| 動的更新 | `MutationObserver(document.body, {childList: true, subtree: true})` が Shiny の reactive 更新を検知し、`requestAnimationFrame` で `renderMathInElement(node)` を逐次実行 |

詳細: [`docs/math_rendering_fix.md`](math_rendering_fix.md)

### 10.4 数値整形

| 項目 | 内容 |
|---|---|
| 実装 | `report/ui_format.py:format_si, pretty_number` |
| 機能 | 11840 V → `11.84\,\text{kV}`、3.8e11 V/s → `3.80\times 10^{11}\,\text{V/s}` |
| SI 接頭辞 | T/G/M/k/(none)/m/μ/n/p の自動切替 |
| 例外 | 複合単位（V/s、Ω、W/m³ 等）は接頭辞付与せず指数表記 |

---

## 11. テスト

`pytest`、合計 **45 passed**。

| ファイル | テスト数 | 内容 |
|---|---|---|
| `test_io.py` | 1 | xlsx → 4 Waveform の往復、Δt 一致 |
| `test_electrical.py` | 6 | 正弦波で P̄=½V₀I₀cosφ、Vrms=V₀/√2、エネルギー一貫性 |
| `test_plasma.py` | 4 | Boltzmann 逆算、Debye/プラズマ周波数オーダー、Stark 単調、Paschen 有限 |
| `test_spectroscopy.py` | 6 | xlsx の H/O/W/Al/Cu の Te を完全再現 |
| `test_advanced_electrical.py` | 8 | パルス検出、Duty、Crest=√2、Form=π/(2√2)、power density |
| `test_oil_synthesis.py` | 5 | SEI/EC/χ/η_SE/ASF α=0.85 復元 |
| `test_nonequilibrium.py` | 5 | E/N の Td 換算、T_vib 逆算 |
| `test_operational.py` | 6 | 1 kW 予算判定の境界値、η_dev、Q_cool |
| `test_validation.py` | 4 | CSV 列欠損、Δt 不均一検出、DC offset 通知 |

実行:
```bash
.venv/bin/pytest -q
# ............................................. [100%]
# 45 passed
```

---

## 12. 文書化レイヤ

ソースコードと並んで `docs/` 配下に 7 本の設計書を保持:

| ファイル | 内容 |
|---|---|
| [`theory_reference.md`](theory_reference.md) | 全 20+ 理論式の式・導出・前提・引用論文 |
| [`ui_redesign_explanation.md`](ui_redesign_explanation.md) | 研究者向け UI 設計の根拠 |
| [`math_rendering_fix.md`](math_rendering_fix.md) | KaTeX 採用までの試行と仕組み |
| [`publish_and_render_plan.md`](publish_and_render_plan.md) | 限定公開インフラ設計 |
| [`ux_redesign_researcher_plan.md`](ux_redesign_researcher_plan.md) | 会議議事録と整合する UX 設計 |
| [`advanced_theory_and_trace_ux_plan.md`](advanced_theory_and_trace_ux_plan.md) | 高次理論式追加と Trace タブ刷新 |
| [`IMPLEMENTATION.md`](IMPLEMENTATION.md) | 本書（実装内容 完全リファレンス） |

これらは本ソフトの「**意思決定ログ**」として機能し、将来の保守者が「なぜそう実装したか」を追える。

---

## 13. 全実装ファイル一覧

```
src/oscillo_plasma_calc/
  __init__.py
  config/
    __init__.py
    constants.py                  # 物理定数
    defaults.yaml                 # Paschen A,B,γ ほか
  io_layer/
    __init__.py
    schema.py                     # Waveform dataclass
    xlsx_loader.py                # xlsx 読込
    csv_loader.py                 # CSV 読込/書込（meta 行対応）
  signal/
    __init__.py
    filtering.py                  # MA / Savitzky-Golay
    peaks.py                      # Vpp/Ipp/t_r/dV/dt
    fft.py                        # rFFT + Hanning
    preprocess.py                 # DC offset / edge sync
  electrical/
    __init__.py
    instant_power.py              # P(t), P_peak
    energy_integral.py            # E, P̄
    rms.py                        # Vrms, Irms
    lissajous.py                  # Manley
    impedance.py                  # Z(t)
    advanced.py                   # ★ E_pulse/Duty/P_eff/⟨|P|⟩/CF/FF/p_vol
  plasma/
    __init__.py
    boltzmann.py                  # 2 本線 Te
    stark.py                      # Stark ne
    debye.py                      # λ_D, f_p
    ohmic.py                      # σE²
    paschen.py                    # V_b
    nonequilibrium.py             # ★ E/N, ⟨ε⟩, Te/Tgas, Tv
  chemistry/
    __init__.py
    g_value.py                    # G
    efficiency.py                 # η
    selectivity.py                # X_k
    oil_synthesis.py              # ★ SEI/EC/χ/η_SE/ASF
  spectroscopy/
    __init__.py
    lines.py                      # 5 元素 24 本 DB
    boltzmann_plot.py             # n 本線 LSM + R²
    csv_loader.py                 # 強度 CSV
  qa/
    __init__.py
    csv_validator.py              # CSV バリデータ
    anomaly.py                    # エラーライン判定
    operational.py                # ★ 1 kW 予算
  symbolic/
    __init__.py
    equations.py                  # sympy で 18 式
  docs/
    __init__.py
    explanations.py               # ★ 3 レベル解説 × 30 物理量
    typical_ranges.py             # ★ 典型範囲 + 範囲外原因 DB
  report/
    __init__.py
    trace.py                      # TraceResult dataclass
    markdown.py                   # Markdown レポート
    ui_format.py                  # ★ format_si / pretty_number
  pipeline.py                     # ★ AnalysisBundle + 自動 anomaly bind
  ui/
    __init__.py
    app.py                        # ★ Shiny アプリ（9 タブ + KaTeX）

tests/
  __init__.py
  test_io.py                      # 1 test
  test_electrical.py              # 6 tests
  test_plasma.py                  # 4 tests
  test_spectroscopy.py            # 6 tests
  test_advanced_electrical.py     # ★ 8 tests
  test_oil_synthesis.py           # ★ 5 tests
  test_nonequilibrium.py          # ★ 5 tests
  test_operational.py             # ★ 6 tests
  test_validation.py              # ★ 4 tests
                                  # ──────────
                                  # 合計 45 tests

scripts/
  convert_xlsx_to_csv.py          # 既存 xlsx → 4 標準 CSV
  run_analysis.py                 # CLI: 波形 → Markdown レポート
  run_excitation_temp.py          # CLI: OES 強度 CSV → Te + plot
  launch_ui.sh                    # mac/Linux Shiny 起動
  launch_ui.bat                   # Windows Shiny 起動

docs/
  IMPLEMENTATION.md               # ★ 本書
  theory_reference.md
  ui_redesign_explanation.md
  math_rendering_fix.md
  publish_and_render_plan.md
  ux_redesign_researcher_plan.md
  advanced_theory_and_trace_ux_plan.md

ルート/
  README.md                       # 初心者向け 3-OS セットアップ
  pyproject.toml                  # 依存定義
  .gitignore                      # xlsx/data_csv/reports 排除
```

---

## 付録 A: 物理量と TraceResult のバインド表

`pipeline._BINDING` で以下のように紐付け（pipeline.py 抜粋）:

```python
"Peak-to-peak voltage Vpp"        : ("vpp", "vpp", "electrical"),
"Energy per pulse E_pulse"        : ("pulse_energy", "pulse_energy", "electrical"),
"Effective average power (Ppeak·D)": ("effective_average_power",
                                       "effective_average_power", "electrical"),
"Specific Energy Input (SEI)"     : ("sei", "sei", "chemistry"),
"Reduced electric field E/N"      : ("e_over_n", "e_over_n", "plasma"),
"Device-wide power budget margin" : ("budget_margin", None, "operational"),
... (合計 30 物理量超)
```

各タプルは `(explanation_key, anomaly_key, category)`。anomaly_key が None の場合は範囲判定をスキップ。

---

## 付録 B: 開発上の補足

### 数値計算の正確性

すべての数値計算は scipy / numpy の確立されたアルゴリズムに依存:
- `scipy.integrate.trapezoid` — 合成台形則 O(Δt²)
- `scipy.fft.rfft` — Cooley–Tukey FFT
- `scipy.signal.find_peaks` — prominence ベース局所最大検出
- `numpy.gradient` — 中央差分（端点片側差分）

自前実装は最小限:
- Shoelace 公式（Lissajous 面積）
- Boltzmann plot 最小二乗法（1 次元なので閉形式）
- DC オフセット平均（先頭 2 % サンプル）

### 単位系

すべて SI 統一。例外:
- T_e: 入出力 eV、内部 K に変換（`config/constants.K_B = 1.380649e-23 J/K` 利用）
- E/N: 内部 V·m²、表示 Td (1 Td = 10⁻²¹ V·m²)
- 時間: 内部 s、UI 表示時に μs/ns 自動変換（`format_si`）

### 拡張時のチェックリスト

新しい物理量を追加する場合:

1. compute 関数を `electrical/` `plasma/` `chemistry/` のいずれかに追加
2. `TraceResult(name, value, unit, equation_latex, substitution_latex, sources)` を返す
3. `docs/explanations.py` に 3 レベル解説を追加
4. `docs/typical_ranges.py` に典型範囲と範囲外原因を追加
5. `pipeline._BINDING` にエントリ追加（key + category）
6. `pipeline.AnalysisBundle` にフィールド追加（必要なら）
7. `analyze_electrical` でその compute 関数を呼ぶ
8. `tests/test_*.py` に検証テストを追加
9. 本書（IMPLEMENTATION.md）にエントリを追加

これで Trace タブに自動的に表示され、KaTeX で式が描画され、エラーライン判定が動く。
