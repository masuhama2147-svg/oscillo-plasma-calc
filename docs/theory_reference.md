# 理論式リファレンス（野村研究室 液中プラズマ 計算ソフト）

本ドキュメントは、`src/oscillo_plasma_calc/` 配下の compute 関数に組み込まれている **すべての理論式** を一元的にまとめたもの。各式について

- **式の形** と **物理的意味**
- **導出の根拠**（前提・仮定）
- **使用場面と適用限界**
- **数値計算での離散化方法**
- **実装ファイル** と **根拠論文**（野村研究室_論文アーカイブ.xlsx 内 ID）

を丁寧に記述する。

---

## 0. 記号・単位の一覧

| 記号 | 意味 | SI単位 |
|---|---|---|
| V(t), I(t) | 放電電圧・電流の時間波形 | V, A |
| P(t) | 瞬時電力 | W |
| E | 投入（吸収）エネルギー | J |
| T | 観測窓の長さ（周期） | s |
| f | 周波数（パルス繰返し PRF または RF） | Hz |
| ω = 2πf | 角周波数 | rad/s |
| q(t) | 累積電荷 ∫I dt | C |
| σ | 電気伝導率 | S/m |
| Te | 電子温度 | K または eV |
| ne | 電子密度 | m⁻³ |
| λ_D | Debye 長 | m |
| f_p | プラズマ周波数 | Hz |
| ε₀ | 真空誘電率 = 8.8542×10⁻¹² | F/m |
| k_B | Boltzmann 定数 = 1.3807×10⁻²³ J/K (または 8.6173×10⁻⁵ eV/K) | J/K |
| e | 電気素量 = 1.6022×10⁻¹⁹ | C |
| m_e | 電子質量 = 9.1094×10⁻³¹ | kg |
| c | 光速 = 2.9979×10⁸ | m/s |
| N_A | Avogadro 数 = 6.0221×10²³ | 1/mol |

すべての定数は [config/constants.py](../src/oscillo_plasma_calc/config/constants.py) に CODATA 値で定義。

---

## 1. Tier 1 — 電気系（オシロ V(t), I(t) のみで計算可能）

### 1.1 ピーク間電圧 Vpp

$$
V_{pp} = V_{\max} - V_{\min}
$$

- **意味**: 1 測定窓内で観測された電圧の振れ幅。双極性駆動なら +Vmax と −Vmin が対称、片寄りがあれば整流性成分を含むと判断。
- **前提**: 単発パルスの最大値取得、またはバースト内の最大振幅評価。繰返しパルスでも「代表 1 発」の振幅として使える。
- **実装**: [signal/peaks.py:detect_vpp](../src/oscillo_plasma_calc/signal/peaks.py) — `np.max`, `np.min` 取得のみ。
- **根拠**: Nomura 2013_CAP-13-1050（ナノ秒パルス破壊特性）。
- **注意**: プローブのベースラインオフセット（DC）が残っていると Vmax/Vmin が両方シフトするので、解析前に中心合わせ（`v -= np.mean(v[:M])` 等）の前処理を推奨。

### 1.2 ピーク間電流 Ipp

$$
I_{pp} = I_{\max} - I_{\min}
$$

- **意味**: 放電チャネルに流れる瞬間電流の最大振れ幅。液中ストリーマでは数十 A クラス（電子なだれ＋イオン流）。
- **前提**: Rogowski コイル等の電流プローブの感度校正が済んでいること。
- **実装**: 同ファイル `detect_ipp`。

### 1.3 立ち上がり時間 t_r (10 → 90 %)

$$
t_r = t\!\left(x = 0.9\,x_{\max}\right) \;-\; t\!\left(x = 0.1\,x_{\max}\right)
$$

- **意味**: パルスの立ち上がりエッジを定義する標準指標。高速電離プロセスの時間スケールを表す。
- **前提**: 波形が単調増加領域を持つこと。リンギングやノイズがあると検出ジッターが出るため、Savitzky–Golay 前処理を推奨。
- **実装**: [signal/peaks.py:rise_time](../src/oscillo_plasma_calc/signal/peaks.py)。`argmax(x >= lo*span)` による単純閾値交差検出。
- **将来改善**: `scipy.signal.find_peaks` + 補間で ns 級精度に引き上げ可能。

### 1.4 ピーク・スルーレート dV/dt, dI/dt

$$
\left.\frac{dV}{dt}\right|_{\max} = \max_k \left|\frac{V_{k+1} - V_{k-1}}{2\Delta t}\right|
$$

- **導出**: 中心差分（2 次精度 O(Δt²)）による数値微分の最大値。
- **意味**: 電圧変化速度の最大値 = 電界印加速度の上限 = ストリーマ前面の伝搬速度を決めるパラメータ。典型値: 液中 ns-pulse で 10¹¹–10¹² V/s。
- **実装**: [signal/peaks.py:slew_rate](../src/oscillo_plasma_calc/signal/peaks.py)。`np.gradient(x)/np.gradient(t)`。
- **適用限界**: サンプリング周波数 f_s の半分（Nyquist = 1/(2Δt)）を超える真のスルーレートは捉えられない。2 ns サンプリングなら最大 250 MHz 成分まで。

### 1.5 瞬時電力 P(t)

$$
P(t) = V(t)\,I(t)
$$

- **導出**: Ohm の法則ではなく **瞬時の電磁エネルギー流入率**。電気回路理論の定義式。
- **物理的意味**: 正なら系（プラズマ＋電極）がエネルギーを吸収、負なら浮遊容量・インダクタンスからの放出。
- **実装**: [electrical/instant_power.py:instantaneous_power](../src/oscillo_plasma_calc/electrical/instant_power.py)。要素積。
- **根拠**: Nomura 2006_JJAP-45-8864, 2011_PSST-20-034016。
- **ピーク電力** `peak_power`: $P_\text{peak} = \max_k |V_k I_k|$。瞬時値の絶対値最大。

### 1.6 吸収エネルギー E

$$
E = \int_{t_0}^{t_N} V(t)\,I(t)\,dt
$$

- **導出**: 瞬時電力の時間積分 = 系に投入されたエネルギー。
- **離散化**（合成台形則）:
$$
E \approx \sum_{k=0}^{N-2} \frac{P_k + P_{k+1}}{2} (t_{k+1} - t_k)
$$
誤差は O(Δt²) かつ境界での端点寄与を正しく扱う。
- **実装**: [electrical/energy_integral.py:absorbed_energy](../src/oscillo_plasma_calc/electrical/energy_integral.py) — `scipy.integrate.trapezoid`。`cumulative_trapezoid` で累積 E(t) も算出。
- **注意**: 観測窓が 1 パルスを丸ごと含むことが前提。窓が短すぎると取りこぼし、長すぎると無放電区間のノイズ成分も積み込む。

### 1.7 時間平均電力 P̄

$$
\bar{P} = \frac{1}{T}\int_0^T V(t)\,I(t)\,dt \;=\; \frac{E}{T}
$$

- **意味**: 「単位時間あたりの平均投入電力」。反応器への熱入力や冷却設計の判断材料。
- **注意事項**: T の取り方で結果が大きく変わる。本ソフトは **観測窓の長さ** を T としているため、繰返しパルス列では「1 周期 = 観測窓」と仮定したときの値。実 PRF（Pulse Repetition Frequency）を入れた評価は Lissajous 法に任せる。
- **実装**: 同ファイル `mean_power`。

### 1.8 RMS（実効値）

$$
V_{\mathrm{rms}} = \sqrt{\frac{1}{T}\int_0^T V(t)^2\,dt},\qquad I_{\mathrm{rms}} = \sqrt{\frac{1}{T}\int_0^T I(t)^2\,dt}
$$

- **物理的意味**: 同じ電力を消費する等価 DC 値。RF プラズマの入力電力評価で必須。
- **正弦波に対する理論値**: $V_{\mathrm{rms}} = V_0/\sqrt{2}$（振幅 V₀）。
- **パルス列に対する値**: デューティ比 D に対し $V_{\mathrm{rms}} \approx V_{\mathrm{peak}}\sqrt{D}$。本ソフトの PW 測定データでは Vrms/Vpp ≈ 0.1、すなわち D ≈ 1 % のパルス列と整合。
- **離散化**: 被積分関数 x² を作ってから台形則で積分、T で割って平方根。
- **実装**: [electrical/rms.py](../src/oscillo_plasma_calc/electrical/rms.py)。

### 1.9 Lissajous（V–q）平均電力 — Manley 法

$$
\bar{P} = f \oint V\,dq,\qquad q(t) = \int_0^t I(t')\,dt'
$$

- **導出**: ある周期 T の間にプラズマへ入るエネルギーは W = ∮V dq（閉曲線の面積）。これを周波数 f（1/T）倍すると平均電力になる。
- **物理的意味**: 誘電体バリア放電（DBD）や誘電体結合系で、オシロの「電荷」として取られる信号（モニタコンデンサ Cm の電圧 × Cm など）と電極電圧のリサージュ図形が **平行四辺形ループ** を描く → その面積 = 1 周期消費エネルギー。
- **歴史**: Manley (1943) による古典法。現代 DBD 研究の標準。
- **本実装の特殊化**: モニタコンデンサが無い場合、q(t) = ∫I(t)dt として **計測電流を直接積分** して疑似電荷とする。液中ストリーマでは DBD の厳密解釈から外れるが、**1 周期エネルギーのオーダー評価** には十分機能する。
- **閉曲線面積の計算**: Shoelace（多角形符号付き面積）公式
$$
\text{Area} = \frac{1}{2}\left|\sum_k V_k\,q_{k+1} - V_{k+1}\,q_k\right|
$$
- **実装**: [electrical/lissajous.py](../src/oscillo_plasma_calc/electrical/lissajous.py)。
- **根拠**: Manley 1943 + Nomura 2013_CAP-13-1050 文脈での応用。

### 1.10 瞬時インピーダンス Z(t)

$$
Z(t) = \frac{V(t)}{I(t)} \qquad (|I(t)| > \text{threshold})
$$

- **意味**: 放電チャネルの時間発展する抵抗率。ストリーマ形成前（絶縁体: kΩ–MΩ）→ 形成中（遷移: Ω–kΩ）→ 形成後（導電性チャネル: Ω 以下）と 2–3 桁ダイナミクスする。
- **I ≈ 0 近傍の扱い**: ゼロ割防止のため閾値（デフォルト 1 mA）未満は NaN。
- **実装**: [electrical/impedance.py](../src/oscillo_plasma_calc/electrical/impedance.py)。

### 1.11 FFT パワースペクトル

$$
X(f) = \int_{-\infty}^{\infty} x(t)\,w(t)\,e^{-j 2\pi f t}\,dt
$$

- **離散化**: 実信号 1 次元 rFFT（`scipy.fft.rfft`）+ Hanning 窓 $w_k = 0.5 - 0.5\cos(2\pi k/(N-1))$ で端点の不連続を軽減（leakage 抑制）。
- **出力（片側振幅スペクトル）**: $A(f) = \dfrac{2}{N}|X(f)|$
- **支配周波数**: DC を除いた最大振幅の周波数を返す。
- **実装**: [signal/fft.py](../src/oscillo_plasma_calc/signal/fft.py)。
- **Nyquist**: f_s = 500 MHz → 解析可能上限 250 MHz。

---

## 2. Tier 2 — プラズマ診断（発光分光データが必要）

### 2.1 Boltzmann 2 本線法による電子温度 Te

$$
\frac{I_{ij}}{I_{kl}} = \frac{g_i\,A_{ij}\,\nu_{ij}}{g_k\,A_{kl}\,\nu_{kl}}\,\exp\!\left[-\frac{E_i - E_k}{k_B T_e}\right]
$$

- **導出**:
  - 熱平衡プラズマで上準位占有数は Boltzmann 分布 $n_i \propto g_i \exp(-E_i/(k_B T_e))$
  - 自発放射強度 $I_{ij} = n_i A_{ij} h\nu_{ij}$
  - 2 本の線の比を取ると、$n_i/n_k = (g_i/g_k)\exp[-(E_i-E_k)/(k_B T_e)]$ だけが残り、これを I 比で表現すると上式になる。
- **前提**:
  1. 局所熱平衡（LTE）または部分的 LTE
  2. 光学的に薄い（自己吸収無視）
  3. 波長校正・感度校正済みのスペクトル強度
- **Te の逆算**:
$$
T_e = -\frac{E_i - E_k}{k_B\,\ln\!\left(\dfrac{I_{ij}/I_{kl}}{\text{prefactor}}\right)}
$$
- **実装**: [plasma/boltzmann.py](../src/oscillo_plasma_calc/plasma/boltzmann.py)。
- **根拠**: Nomura 2006_JJAP-45-8864, 2009_JAP-106-113302。
- **限界**: 2 本線法は誤差が大きい（典型 ±30%）。n 本線を使う Boltzmann plot（後述 4.1）の方が精度が高い。

### 2.2 Stark 広がりによる電子密度 ne

$$
n_e = \alpha(T_e)\,(\Delta\lambda_{1/2})^{3/2}
$$

- **導出**: Stark 効果 — 水素の H_α (656.3 nm) は電子衝突による Stark 広がりが支配的で、線幅の 3/2 乗が ne に比例する（Griem, 1964）。
- **Stark 係数** α: Te 依存。大気圧水プラズマでは α ≈ 10²³ m⁻³·nm⁻³/² が典型（本実装のデフォルト）。精密測定では Te を先に決めてから対応する α を文献表から引く。
- **入力**: H_α 線の FWHM（半値全幅）Δλ_{1/2} [nm]
- **実装**: [plasma/stark.py](../src/oscillo_plasma_calc/plasma/stark.py)。
- **根拠**: Nomura 2009_POP-16-033503。

### 2.3 Debye 長 λ_D

$$
\lambda_D = \sqrt{\frac{\varepsilon_0\,k_B\,T_e}{n_e\,e^2}}
$$

- **導出**: Poisson 方程式と Boltzmann 占有を組合せ、点電荷のまわりの静電遮蔽距離として得られる古典的結果。
- **意味**: プラズマが「準中性バルク」として振る舞える最小スケール。λ_D ≪ ギャップサイズ → 正常なプラズマ、λ_D ≳ ギャップサイズ → sheath のみ（true plasma 無し）。
- **典型値**: Te = 1 eV, ne = 10²² m⁻³ → λ_D ≈ 74 nm。
- **実装**: [plasma/debye.py:debye_length](../src/oscillo_plasma_calc/plasma/debye.py)。
- **Te の変換**: Te [eV] = Te [K] × k_B [eV/K]。本実装は eV 入力を内部で K に換算してから代入。

### 2.4 電子プラズマ周波数 f_p

$$
f_p = \frac{1}{2\pi}\sqrt{\frac{n_e\,e^2}{m_e\,\varepsilon_0}}
$$

- **導出**: 電子流体の線形化方程式から、中性バックグラウンド中の集合振動の固有振動数として出る。
- **意味**: 外部電磁波の角周波数 ω と f_p の関係で、**ω < 2π f_p なら遮蔽（反射）、ω > 2π f_p なら透過**。
- **例**: ne = 10²² m⁻³ → f_p ≈ 900 GHz ≫ 2.45 GHz → マイクロ波はプラズマ表面でほぼ反射／吸収される（スキン効果）。
- **実装**: [plasma/debye.py:plasma_frequency](../src/oscillo_plasma_calc/plasma/debye.py)。
- **根拠**: Nomura 2008_APEX-1-046002（RF vs MW 比較）。

### 2.5 Ohmic 加熱密度

$$
p_{\mathrm{ohm}} = \sigma\,E^2
$$

- **導出**: 電流密度 $J = \sigma E$、単位体積のパワー散逸 $p = J\cdot E$。
- **意味**: 導電性液体内での局所 Joule 加熱。σ は液体自身の導電率（純水 ~10⁻⁴ S/m、水道水 ~10⁻² S/m、電解質水溶液 > 1 S/m）、E は局所電界。
- **典型値**: σ = 0.01 S/m × E = 10⁶ V/m → p_ohm = 10¹⁰ W/m³ = 10 GW/m³ = 10 kW/cm³。数 mm³ 範囲で数百 W 投入 → 気泡形成の駆動力。
- **実装**: [plasma/ohmic.py](../src/oscillo_plasma_calc/plasma/ohmic.py)。
- **根拠**: Nomura 2011_PSST-20-034016（液体導電率がプラズマ特性に与える影響）。

### 2.6 Paschen 破壊電圧

$$
V_b = \frac{B\,p\,d}{\ln(A\,p\,d) - \ln\!\ln\!\left(1 + \dfrac{1}{\gamma}\right)}
$$

- **導出**: Townsend 理論で、pd（圧力 × ギャップ）に対して破壊電圧が極小値をもつ関係。
  - 第 1 Townsend 係数 α と第 2 Townsend 係数 γ（陰極二次電子放出）の相互作用から導出
  - 空気の経験値: A = 112.5 (Pa·m)⁻¹, B = 2737.5 V/(Pa·m)
- **意味**: ギャップ d と圧力 p を決めれば、放電開始に必要な最小電圧が予測できる。pd が小さすぎ（希薄 or 狭ギャップ）・大きすぎ（高圧 or 広ギャップ）の両端で V_b が大きくなり、中間（pd ≈ 数 Pa·m）で最小となる。
- **液中への適用**: Paschen 則は厳密には気相向け。**液中の場合は bubble dynamics と電気導電率が支配**し、経験パラメータ A, B を気相のまま使うと数倍の誤差が出る。本ソフトは「気相参照」として提示する用途。
- **実装**: [plasma/paschen.py](../src/oscillo_plasma_calc/plasma/paschen.py)。
- **根拠**: Nomura 2013_CAP-13-1050。

---

## 3. Tier 3 — 化学・反応評価（GC データが必要）

### 3.1 G 値（100 eV あたりの生成分子数）

$$
G = \frac{N_{\mathrm{prod}}}{E_{\mathrm{abs}} / 100\,\text{eV}}
$$

- **意味**: 放射線化学由来の普遍指標。100 eV（≈ 1 分子の化学結合エネルギーの 10 倍程度）が吸収されるとき何分子の目的種ができるか。
- **入力**: 生成モル数 n_prod と吸収エネルギー E_abs [J]。N_prod = n_prod × N_A。E_abs は E_abs [eV] = E_abs [J] / e。
- **典型値**: 液中プラズマの H₂ 生成で G = 1–10。触媒効果で G > 10 もあり得る。G < 0.5 ならエネルギー効率悪化シグナル。
- **実装**: [chemistry/g_value.py](../src/oscillo_plasma_calc/chemistry/g_value.py)。
- **根拠**: Nomura 2012_IJHE-37-16000, 2020_JJIE_99-104。

### 3.2 化学エネルギー変換効率 η

$$
\eta_{\mathrm{chem}} = \frac{\Delta H \cdot n_{\mathrm{prod}}}{E_{\mathrm{plasma}}}\times 100\,\%
$$

- **意味**: 投入プラズマエネルギーのうち、目的化学反応のエンタルピー ΔH として回収された割合。
- **典型値**: 液中 CO₂ 還元 → メタノールで η = 5–15 %。20% 超は触媒協調・超音波併用が効いている。
- **実装**: [chemistry/efficiency.py](../src/oscillo_plasma_calc/chemistry/efficiency.py)。
- **根拠**: Nomura 2017_JEPE-10-335。

### 3.3 生成物選択性

$$
X_k = \frac{n_k}{\sum_j n_j}
$$

- **意味**: 全生成物中での目的成分のモル分率。液中 CO₂ 還元では CH₃OH 選択性 > 50 % が油合成の実用目標。
- **実装**: [chemistry/selectivity.py](../src/oscillo_plasma_calc/chemistry/selectivity.py)。
- **根拠**: Nomura 2019_IJHE_44-23912。

---

## 4. 励起温度モジュール（spectroscopy/）

### 4.1 Boltzmann plot（n 本線 最小二乗法）

同一元素・同一電離段階の複数スペクトル線から Te を高精度で決める方法（本プロジェクトの中核で、`励起温度計算シート ver.2.xlsx` と数値一致）。

#### 理論式の展開

Boltzmann 占有 + 自発放射強度から:

$$
I_i = C\,g_i\,A_i\,\nu_i\,\exp\!\left[-\frac{E_{u,i}}{k_B T_e}\right]
$$

両辺の対数を取って整理:

$$
\underbrace{\ln\!\frac{I_i}{g_i A_i \nu_i}}_{y_i} = -\frac{1}{k_B T_e}\underbrace{E_{u,i}}_{x_i} + \ln C
$$

（本来 x は E_u だが、**同一元素で下準位を共有する遷移群** なら `x_i = E_{u,i} - E_{l,i}` としても傾きは変わらないため、xlsx に合わせて差分を採用）

#### 最小二乗法による傾き m

n 本の有効線（I_i > 0）に対して
$$
m = \frac{n\sum_i x_i y_i - \sum_i x_i \sum_i y_i}{n\sum_i x_i^2 - (\sum_i x_i)^2}
$$

#### 励起温度

$$
T_e = -\frac{1}{k_B\,m}  \quad\text{(with } k_B = 8.6173\times 10^{-5}\,\text{eV/K)}
$$

#### 入力データベース（本ソフトに組み込み済み）

| 元素 | 線 | 備考 |
|---|---|---|
| H I | H_α 656.279, H_β 486.135, H_γ 434.047 nm | すべて下準位 2p 共通 |
| O I | O1–O6 (777, 844 nm 群) | 2 つの多重項 |
| W I | W1–W5 (321–429 nm) | UV/可視 |
| Al I | Al1–Al5 (308–669 nm) | |
| Cu I | Cu1–Cu5 (324–521 nm) | |

各線の $\lambda, E_u, E_l, g, A$ は [spectroscopy/lines.py](../src/oscillo_plasma_calc/spectroscopy/lines.py) に NIST / xlsx 準拠で収録。

#### 線の周波数

$$
\nu_i = \frac{c}{\lambda_i}
$$
（c = 2.9979×10⁸ m/s、λ は nm → m 換算）

#### 線を除外する慣例

強度 I_i = 0 を入れると、そのスペクトル線はフィッティングから除外（xlsx `J=0 で除外` と同じ挙動）。

#### 実装

- [spectroscopy/boltzmann_plot.py](../src/oscillo_plasma_calc/spectroscopy/boltzmann_plot.py)
- [spectroscopy/lines.py](../src/oscillo_plasma_calc/spectroscopy/lines.py)

#### 根拠論文

- 2006_JJAP-45-8864（Nomura lab 水中 RF プラズマ、温度分布）
- 2009_JAP-106-113302（空間分解 OES）
- 励起温度計算シート ver.2.xlsx（野村研究室社内リファレンス）

---

## 5. 数値計算の離散化手法まとめ

| 処理 | 手法 | 誤差 | 実装 |
|---|---|---|---|
| 積分 ∫ x dt | 合成台形則 | O(Δt²) | `scipy.integrate.trapezoid` / `cumulative_trapezoid` |
| 微分 dx/dt | 中心差分（内部）+ 片側差分（境界） | O(Δt²) | `numpy.gradient` |
| FFT | rFFT + Hanning 窓 | leakage は窓で抑制 | `scipy.fft.rfft` |
| Lissajous 面積 | Shoelace 公式 | 離散多角形そのもの | 自前実装 |
| ピーク検出（Vpp） | 全域最大・最小 | 観測ノイズに感度あり | `np.max`, `np.min` |
| 立ち上がり時間 | 最初に閾値を超えたインデックス | Δt 精度 | `np.argmax(x >= thresh)` |
| 最小二乗法（Boltzmann） | 閉形式（n > 1） | 数値誤差のみ | 手書き（sum ベース） |

---

## 6. 物理定数（config/constants.py から）

```
ε₀ = 8.8541878128e-12  F/m      (CODATA)
μ₀ = 1.25663706212e-6  N/A²
k_B = 1.380649e-23     J/K      (exact SI definition)
    = 8.61733363326e-5 eV/K     (for Boltzmann plot)
e   = 1.602176634e-19  C        (exact SI definition)
m_e = 9.1093837015e-31 kg
m_p = 1.67262192369e-27 kg
c   = 2.99792458e8     m/s      (exact)
h   = 6.62607015e-34   J·s      (exact SI definition)
N_A = 6.02214076e23    1/mol    (exact SI definition)
```

Avogadro 数や Boltzmann 定数は 2019 年の SI 再定義で「定義値」となっており、以降改定されない。

---

## 7. 根拠論文早見表（野村研究室_論文アーカイブ.xlsx ID）

| 論文 ID | 関与する理論式 |
|---|---|
| 2006_JJAP-45-8864 | Boltzmann 2 本線法 / Boltzmann plot / 瞬時電力 |
| 2007_JAP-101-093303 | 超臨界 CO₂ プラズマ（圧力依存の拡張） |
| 2008_APEX-1-046002 | 吸収エネルギー / 平均電力 / プラズマ周波数（RF vs MW） |
| 2009_JAP-106-113302 | 空間分解 OES による Te 分布 |
| 2009_POP-16-033503 | Stark 広がりによる ne |
| 2011_PSST-20-034016 | Ohmic 加熱密度 / 液体導電率効果 |
| 2012_IJHE-37-16000 | G 値（メタンハイドレート） |
| 2013_CAP-13-1050 | Vpp, dV/dt, 立ち上がり時間 / Lissajous / Paschen |
| 2017_JEPE-10-335 | 化学変換効率 η |
| 2019_IJHE_44-23912 | 生成物選択性 X |
| 2020_JJIE_99-104 | G 値 / η（アンモニア合成） |
| Manley 1943 | Lissajous V–q 法の古典 |

---

## 8. 適用外（将来拡張で追加すべき理論式）

現行システムでまだ実装していないが、液中プラズマ CO₂ 還元研究で必要になる理論式:

1. **EEDF（電子エネルギー分布関数）** — Boltzmann 方程式の数値解。BOLSIG+ 互換の入出力を用意すると研究幅が広がる。
2. **反応速度モデル** — Arrhenius 式 $k = A\exp(-E_a/(RT))$ を用いた CO₂ → CO + O の時間発展モデル。
3. **バブルダイナミクス** — Rayleigh–Plesset 方程式で液中気泡の動的成長を追う。
4. **誘電率・電気伝導率の温度依存** — 水の σ(T) は Arrhenius 型、ε(T) は Debye モデルで補正可能。
5. **Fischer–Tropsch 収率モデル** — syngas (H₂+CO) → 液体炭化水素の選択性を記述する ASF 分布。

これらは [ui_redesign_explanation.md](ui_redesign_explanation.md) で議論している Tier 4 相当の拡張トピック。

---

## 9. 実装と理論の対応チェックリスト

理論式が実装と食い違わないよう、新しい式を追加したら必ずチェック:

- [ ] 式を LaTeX 表現で `sympy` に登録（[symbolic/equations.py](../src/oscillo_plasma_calc/symbolic/equations.py)）
- [ ] compute 関数が `TraceResult(value, unit, equation_latex, substitution_latex, sources=[...])` を返す
- [ ] 数値検証テスト（`tests/test_*.py`）で既知解との一致確認
- [ ] 本ドキュメントに式・導出・実装ファイル・根拠論文を追記
- [ ] README に UI タブ／CLI コマンドの使い方を追加

---

## 参考文献

- NIST Atomic Spectra Database: https://physics.nist.gov/asd（Einstein A, E_u, g の原典）
- Griem, H. R. "Plasma Spectroscopy" (1964)（Stark 理論の古典書）
- Raizer, Y. P. "Gas Discharge Physics" (1991)（Paschen/Townsend）
- 野村研究室 論文アーカイブ（社内 xlsx）
