# Phase 5+ NASA PAC91 / CEA / Cantera / BOLSIG+ 統合 完全技術レポート

**日付**: 2026-05-02
**対象**: 野村研究室 液中プラズマ オシロスコープ波形 & 発光分光 解析ソフトを Nomura Plasma Thermo-Chemical Twin へ拡張
**目的**:
1. NASA PAC91（熱力学関数生成）/ NASA CEA（化学平衡）/ Cantera（反応速度）/ BOLSIG+（EEDF）の統合方針
2. 実装上の **技術的懸念点・課題** をプロフェッショナル視点で網羅
3. 必要となる **理論計算式 / 学習データ / 合成データ** を具体的に列挙
4. **手動実装が必要なタスク**（自動化不可な部分）を明示
5. フロント表示の懸念点とリスク

---

## エグゼクティブサマリ

| 評価軸 | 現状 | Phase 5+ 完了想定 |
|---|---|---|
| 計算層の数値精度 | A+（NASA grade） | A+（維持） |
| 熱力学・化学平衡 | 未対応 | NASA PAC91/CEA グレード |
| 反応経路解析 | 未対応 | Cantera ReactionPathDiagram |
| EEDF 厳密化 | 経験式（0.02·E/N） | BOLSIG+ 数値解 |
| 推定実装工数 | — | **約 8〜12 週間** |
| 推定追加コード量 | 約 6,500 行 | **+12,000〜15,000 行** |
| 想定リスク | 低（土台のみ） | **中〜高**（外部依存・データ整備） |

**結論**: 進めて良いが、**学習データ・合成データの整備が最大のボトルネック**。コード実装は CI/QA で自動化できるが、熱力学データベースと反応断面積データは研究室外部からの供給が必須で、ここで詰まる可能性が高い。

---

## 1. 直近のスクショから判明した追加バグ

### 1.1 🔴 致命: FFT タブの x 軸が `10^243` まで伸びる

**症状**: `frequency [MHz]` 軸が `1, 10^27, 10^54, ..., 10^243` で表示。実際のデータ範囲（0–250 MHz）と完全に乖離。

**原因確定**（root cause analysis）:
- `freq_v[0] = 0` (DC 成分) が `xaxis=dict(type="log")` と組み合わさると Plotly の auto-range が `log(0) = -inf` で破綻
- 結果として軸の最大値が浮動小数点の表現限界近くまで膨張

**修正済み** (`ui/app.py:fft_plot`):
```python
# DC ビンを除外 + range を [first_nonDC_bin, Nyquist] に固定
v_mhz = freq_v[1:] / 1e6
fig.update_layout(
    xaxis=dict(type="log",
               range=[np.log10(x_min), np.log10(nyq_mhz)]),
)
```

**この種のバグが他にも潜んでいる可能性**:
- どの log scale 軸でも `0` を含むと類似バグ → Phase 5 の Equilibrium タブで species mole fraction が 0 を含む場合は注意
- impedance Z(t) で `I→0` 時の log 表示で同様の問題が起きうる

### 1.2 🟠 励起温度タブの空 Boltzmann plot が大きすぎる

スクショを見ると、データ未投入時のプレースホルダプロットがタブ右側の大半を占めている。研究者にとって「何を入力すべきか」より「空のプロット」の方が目立つのは UX として弱い。

**改善案**: 未投入時は plot を出さず、入力ガイドを大きく出す（次の Phase 0.8 として実装可能）。

---

## 2. NASA PAC91 統合の理論実装計画

### 2.1 PAC91 とは何か

PAC91（Properties And Coefficients, 1991）は NASA Glenn Research Center が公開した **熱力学関数生成プログラム**。論文・ロケット工学で 30 年以上使われている標準。

**入力**: 分子定数（振動数・回転定数・電子準位・縮退度）
**出力**: NASA 多項式係数（7 係数版・9 係数版）

中間プロセス:
```
分子定数
  ↓ 統計力学
分配関数 Q(T)
  ↓ 微分
Cp(T), H(T), S(T), G(T)
  ↓ 最小二乗フィット
NASA polynomial coefficients
  ↓
Cantera / CEA / 反応器シミュレーション
```

### 2.2 実装すべき理論式（11 式）

| # | 式 | 意味 | 実装難度 |
|---|---|---|---|
| 1 | $Q_\text{trans}(T) = \left(\frac{2\pi m k_B T}{h^2}\right)^{3/2} V$ | 並進分配関数 | 低 |
| 2 | $Q_\text{rot,linear}(T) = \frac{T}{\sigma\Theta_r}$ | 線形分子の回転分配関数 | 低 |
| 3 | $Q_\text{rot,nonlinear}(T) = \frac{\sqrt{\pi}}{\sigma}\sqrt{\frac{T^3}{\Theta_A\Theta_B\Theta_C}}$ | 非線形分子 | 中 |
| 4 | $Q_\text{vib}(T) = \prod_i \frac{1}{1 - e^{-\Theta_{v,i}/T}}$ | 調和振動分配関数 | 低 |
| 5 | $Q_\text{vib,anh}(T)$ | **非調和性補正**（PAC91 の特徴） | **中〜高** |
| 6 | $Q_\text{elec}(T) = \sum_i g_i \exp(-E_i/k_B T)$ | 電子分配関数 | 低 |
| 7 | $C_p/R = \frac{d}{dT}\left[T \frac{d\ln Q}{dT}\right] + 1$ | 熱容量 | 低 |
| 8 | $H/(RT) = T\frac{d\ln Q}{dT} + 1$ | エンタルピー | 低 |
| 9 | $S/R = \ln Q + T\frac{d\ln Q}{dT}$ | エントロピー | 低 |
| 10 | $G/(RT) = -\ln Q + 1$ | 自由エネルギー | 低 |
| 11 | **Wilhoit 高温外挿**: $C_p/R = a + (b - a)y^2[1 + (y-1)\sum c_i y^i]$, $y = T/(T+T^*)$ | 高温域 安定外挿 | **高** |

NASA 7 係数多項式（Cantera 標準）:
$$\frac{C_p}{R} = a_1 + a_2 T + a_3 T^2 + a_4 T^3 + a_5 T^4$$
（低温領域 + 高温領域の 2 セット = 14 係数）

NASA 9 係数版:
$$\frac{C_p}{R} = a_1 T^{-2} + a_2 T^{-1} + a_3 + a_4 T + a_5 T^2 + a_6 T^3 + a_7 T^4$$
（より広温域、cryogenic から 20,000 K まで）

### 2.3 実装モジュール構造（提案）

```
src/oscillo_plasma_calc/thermo/
├── __init__.py
├── species.py              # Species dataclass: name, formula, M, Tmin/Tmax, NASA coeffs
├── partition.py            # PartitionFunction protocol (translation/rotation/vibration/electronic)
├── nasa_poly.py            # NASA7 / NASA9 evaluator (cp_R, h_RT, s_R, g_RT)
├── wilhoit.py              # WilhoitCp 高温外挿
├── thermo_fit.py           # Q(T) → NASA polynomial 最小二乗フィット
├── equilibrium_constants.py# logK(T) = -ΔG/(RT·ln10)
├── cantera_export.py       # Species YAML 出力（Cantera 互換）
├── database.py             # JANAF / NASA9 / Burcat DB ローダ
└── validators.py           # 温度範囲外、Cp 負値、単調性違反などのチェック
```

### 2.4 必要な学習・合成データ

**A. 既存公開 DB から取り込むべきもの**:

| データセット | サイズ | ライセンス | 用途 |
|---|---|---|---|
| **NASA Glenn ThermoBuild** ([URL](https://cearun.grc.nasa.gov/ThermoBuild/)) | ~2,000 species, NASA9 | 公開 | 主要参照 |
| **Burcat's Thermodynamic Database** (TUM) | ~1,500 species, NASA7+9 | CC-BY | 補完 |
| **JANAF Thermochemical Tables** (NIST) | ~1,800 species, table 形式 | NIST 公開 | クロス検証 |
| **GRI-Mech 3.0 thermo.dat** | ~50 species (CH4 系) | 公開 | 反応機構と整合 |
| **NASA CEA thermo.inp** | CEA 同梱、~3,000 species | 公開 | CEA 互換性 |

**B. 油合成研究で特に必要な species（28 種）**:

```
無機:    H2, O2, H, O, OH, H2O, H2O2, HO2, e-
酸化炭素:CO, CO2, HCO, CHO, CHO2
炭素   : C(s), C, CH, CH2, CH3, CH4
アルコール:CH3OH, C2H5OH, C3H7OH(iso/n)
炭化水素:C2H2, C2H4, C2H6, C3H6, C3H8, C4H10
ラジカル:CH2OH, CH3O, CH3CO, C2H5
凝縮相 :H2O(L), CH3OH(L), C2H5OH(L), C(graphite), C(amorphous), Cu, CuO, Cu2O,
        Fe, Fe3O4, Fe2O3, W, WO3
```

**C. 合成データが必要な場面**:

1. **Wilhoit 外挿の検証**: 同じ species で高温外挿前後の Cp の連続性を試すため、低温域 NASA7 → Wilhoit 高温域 への接続テストを **解析的に作った合成データ**（既知の振動数からの理論 Cp）で検証
2. **未知 C2-C4 species の仮物性**: ASF α=0.85 で連鎖伸長した炭化水素の物性を、Group Additivity（Benson 則）で合成

### 2.5 実装上の懸念点

⚠ **懸念 1: Wilhoit 外挿の安定性**
PAC91 のオリジナルでは Wilhoit パラメータ a, b, c_i, T* を非線形フィットで決める。SciPy `optimize.least_squares` で実装可能だが、**初期値依存性が強い**。失敗ケースを検出してユーザーに通知する仕組みが必要。

⚠ **懸念 2: NASA9 係数の温度範囲分割**
NASA9 は 200-1000 K / 1000-6000 K / 6000-20000 K の 3 区間。境界での Cp の連続性は保証されているが **2 階導関数は不連続**。研究者が「高温域で Cp が滑らかでない」と気にする可能性 → 表示時に区間境界を明示すべき。

⚠ **懸念 3: 単原子ガス vs 多原子ガスの分配関数の扱い**
PAC91 は「単原子は電子準位だけ」「2 原子は剛体回転 + 調和振動 + 補正」「多原子は厳密解」と分けて扱う。**モジュール初期実装で多原子の厳密解を入れない判断** をした場合、UI に「精度: 簡易/精密」フラグを必ず出す。

⚠ **懸念 4: 自己無撞着な熱力学整合性**
ΔH_f, ΔG_f, S° をそれぞれ独立に計算すると、ΔG = ΔH − TΔS の関係が誤差を持って成立しない。**整合性検査** を必ず実装し、誤差 > 0.1 % で警告。

---

## 3. NASA CEA 統合の理論実装計画

### 3.1 CEA とは何か

CEA（Chemical Equilibrium with Applications）は NASA Glenn が公開した **化学平衡組成計算プログラム**。1996 年初版以来、ロケット推進・燃焼・プラズマ化学の標準ツール。

**問題タイプ**（液中プラズマで使う 3 つに絞る）:

| 問題タイプ | 入力 | 出力 | 油合成での用途 |
|---|---|---|---|
| **TP** | T, P, reactants | 平衡組成、各 species mole fraction | 気泡内温度・圧力からの平衡上限 |
| **HP** | H (enthalpy), P, reactants | 断熱到達温度、組成 | パルスエネルギー注入後の温度推定 |
| **UV** | U (internal energy), V, reactants | 組成 | 閉鎖気泡近似 |

### 3.2 実装すべき理論式（10 式）

#### 3.2.1 Gibbs 自由エネルギー最小化（CEA の核）

目的関数:
$$G/(RT) = \sum_i n_i \mu_i^\text{red}(T, P, n)$$

化学ポテンシャル:
$$\mu_i^\text{red}(T, P, n) = \frac{G_i^\circ(T)}{RT} + \ln\frac{n_i}{n} + \ln\frac{P}{P_0}$$

制約（元素保存）:
$$\sum_i a_{ki} n_i = b_k \quad (k = 1, ..., M)$$

$a_{ki}$ = species $i$ に含まれる元素 $k$ の数、$b_k$ = 元素 $k$ の総モル数。

#### 3.2.2 解法アルゴリズム（CEA の元素ポテンシャル法）

CEA は **Lagrange 乗数 $\lambda_k$（element potentials）** を導入して反復:

$$\frac{n_i}{n} = \exp\left[-\frac{G_i^\circ}{RT} - \ln\frac{P}{P_0} + \sum_k a_{ki}\lambda_k - 1\right]$$

Newton-Raphson で $\lambda_k$ を更新。**収束条件**:
- 元素保存誤差 $< 10^{-6}$
- $\Delta G/(nRT) < 10^{-9}$

#### 3.2.3 凝縮相判定（液中プラズマで重要）

凝縮相挿入条件: その species の駆動力（Lagrange ポテンシャルの組合せ）が **その species の純粋 Gibbs より大きい**:

$$\frac{G_s^\circ(T)}{RT} - \sum_k a_{ks}\lambda_k < 0$$

成立すれば Gibbs を下げられるので「凝縮相を追加する」と判断。

**油合成研究での意味**:
- C(s) graphite の挿入 ⇔ 炭素析出（soot）が起こる
- Cu2O / WO3 の挿入 ⇔ 電極材料の酸化進行
- H2O(L) の挿入 ⇔ 液相回帰（プラズマ消滅領域）

### 3.3 実装モジュール構造

```
src/oscillo_plasma_calc/equilibrium/
├── __init__.py
├── problem.py              # ProblemSpec dataclass: type, T, P, H, U, V, reactants
├── reactants.py            # Reactant: name, mole/mass, T_in
├── species_selector.py     # only / omit / insert 機能
├── gibbs_minimizer.py      # 元素ポテンシャル法 Newton-Raphson 実装
├── condensed_phase.py      # 凝縮相挿入テスト
├── mixture_properties.py   # γ, c_p, M_avg, sound speed
├── transport_mixture.py    # 粘度、熱伝導率、Prandtl
├── cea_input.py            # CEA 互換 .inp パーサ (option)
├── cea_output.py           # 結果フォーマッタ
└── validators.py           # 元素保存検証、収束チェック
```

### 3.4 学習・合成データ

**A. CEA 公式 example fixture**:

CEA のマニュアル `RP-1311` には **40 個以上の検証例** が載っている。これを fixtures として埋め込み:

```
tests/fixtures/cea_examples/
├── ex01_h2_o2_combustion_3000K.json     # H2/O2, T=3000K, 1 atm
├── ex02_ch4_o2_stoich.json              # CH4/O2 stoichiometric
├── ex03_co2_h2_reduction.json           # ★ CO2/H2, 油合成本命
├── ex04_co_h2_methanol.json             # ★ CO/H2 → CH3OH 候補
├── ex05_aluminum_combustion.json        # 凝縮相 Al2O3 検証
├── ...（40+ ケース）
```

各 fixture には CEA 公式出力の mole fraction を $\pm 1\%$ で再現することを CI で要求。

**B. 油合成研究で必要な合成データ**:

1. **CO2/H2 系の Pareto front**: SEI vs χ_CO2 の散布図を 50 条件で生成
   - 入力 SEI: 100, 200, ..., 2000 kJ/mol
   - 入力 H2/CO2 比: 0.5, 1, 2, 3, 4, 5
   - 出力: 平衡組成（CO, CH3OH, CH4, C2+, soot indicator）
2. **温度スキャン**: T = 1000, 2000, ..., 8000 K
3. **圧力スキャン**: P = 0.1, 1, 10, 100 atm

これら合成データを生成する CLI を `scripts/generate_cea_benchmark.py` として整備。

### 3.5 実装上の懸念点

⚠ **懸念 1: Newton-Raphson の発散**
初期推定が悪いと発散する。CEA では **段階的初期化**（最初は理想気体近似、徐々に厳密化）を採用しているが、これを Python で安定実装するのは数週間かかる可能性。**SciPy `scipy.optimize.minimize` で SLSQP** から始めて、徐々にカスタム実装へ移行する段階的アプローチが安全。

⚠ **懸念 2: 凝縮相切替時の振動**
凝縮相を出し入れすると、Gibbs エネルギーが不連続に変化する。**ヒステリシス**（一度入れたら閾値より下がるまで抜かない）が必要。CEA も実装している。

⚠ **懸念 3: 数値精度**
mole fraction が 1e-300 級になると `log` で破綻。下限クランプ（`max(x, 1e-30)`）が必須だが、これによる **質量保存の系統誤差** が出る。研究者には「数値クランプにより微量 species は信頼度低」と明示する。

⚠ **懸念 4: Cantera との解の不一致**
Cantera にも `equilibrate('TP')` があるが、内部実装が異なるため数値が CEA と数 % ずれる。**「Cantera と CEA-like 自前実装の両方で計算して、差分が小さいかを表示する」** デュアル検証 UI を提案。

---

## 4. Cantera 統合

### 4.1 役割の切り分け

| 機能 | 自前実装 | Cantera 任せ |
|---|---|---|
| 熱力学関数 (Cp/H/S/G) | ✓ | ✓ |
| NASA polynomial 評価 | ✓ | ✓ |
| 平衡計算 | ✓（CEA-like） | ✓（参照実装） |
| **反応速度（時間発展）** | × | **✓** |
| **ReactionPathDiagram** | × | **✓** |
| **Sensitivity analysis** | × | **✓** |
| **YAML format** | export のみ | full I/O |

### 4.2 必要な反応機構

**油合成のターゲット機構**:

| 機構 | 規模 | 用途 |
|---|---|---|
| **GRI-Mech 3.0** | 53 species, 325 反応 | CH4 燃焼・改質の標準 |
| **USC II** | 111 species | C1-C4 詳細燃焼 |
| **AramcoMech 2.0** | ~500 species | より詳細 |
| **野村研独自** | ~30 species | 液中プラズマ低温反応 |

最初は GRI-Mech 3.0 から始め、徐々に拡張。

### 4.3 Reaction Path Diagram の生成

```python
import cantera as ct
gas = ct.Solution('gri30.yaml')
gas.TPX = 3000, ct.one_atm, 'CO2:0.5, H2:0.5'
diagram = ct.ReactionPathDiagram(gas, 'C')  # 炭素元素フラックス
diagram.title = 'Carbon flux at 3000 K'
diagram.show_details = True
diagram.threshold = 0.05
diagram.write_dot('carbon_paths.dot')
# 別途 graphviz (subprocess.run(['dot', '-Tpng', ...])) で PNG 化
```

### 4.4 Cantera 実装の懸念点

⚠ **懸念 1: graphviz の OS 依存**
`dot` コマンドが必要。Windows では事前 install が必要 → **README に追記が要る**。

⚠ **懸念 2: 機構ファイルのライセンス**
GRI-Mech は LLNL のライセンスで「研究利用可、商用 OK、再配布注意」。リポジトリには **直接コミットせず**、初回起動時にダウンロードする方式が無難。

---

## 5. BOLSIG+ / LXCat 統合

### 5.1 BOLSIG+ とは

BOLSIG+ は **弱電離プラズマの電子 Boltzmann 方程式ソルバー**。E/N、ガス組成、断面積データから:
- EEDF（電子エネルギー分布関数）
- 電子移動度 μ
- 拡散係数 D
- 各反応の rate coefficient

を計算する。

### 5.2 統合方法

```
src/oscillo_plasma_calc/plasma/eedf/
├── __init__.py
├── bolsig_runner.py        # BOLSIG+ binary を subprocess で呼ぶ
├── lxcat_parser.py         # LXCat 断面積 .txt フォーマット
├── eedf_table.py           # 結果のテーブル化
├── electron_impact.py      # rate coefficient → Cantera 反応 rate
└── mock_eedf.py            # BOLSIG+ 無しでも動くフォールバック
```

### 5.3 必要な断面積データ

LXCat（公開 DB）から取得:

| データセット | species | 反応 | URL |
|---|---|---|---|
| Phelps | He, Ar, N2, O2 | 弾性、励起、電離 | lxcat.net |
| IST-Lisbon | CO2, CH4, H2 | 詳細 | lxcat.net |
| BIAGI | Ar, Ne | 弾性 | lxcat.net |

### 5.4 懸念点

⚠ **懸念 1: BOLSIG+ binary の配布**
公式 binary は Windows / Linux 提供だが、**Apple Silicon (M4 Mac) は非対応**。x86_64 Mac は Rosetta 2 で動くが M4 では動かない。**Python で Boltzmann 方程式を直接解く `bolos` ライブラリ** をフォールバックとして用意。

⚠ **懸念 2: 二項近似の限界**
BOLSIG+ は弱電離・一様電場・二項近似前提。液中プラズマの **気泡界面** では局所電場が極端、二項近似が破綻する可能性。**警告を UI に明示**。

⚠ **懸念 3: 計算時間**
BOLSIG+ の 1 回の計算は数秒。E/N をパラメータ掃引すると 100 点 × 5 秒 = 8 分。**事前計算 + lookup table** で対応。

---

## 6. UI/フロント実装の懸念点（プロフェッショナル視点）

### 6.1 既存 UI の構造的限界

#### 限界 1: タブが横一列で 9 個（10+ になる予定）

**問題**: Phase 5+ で Thermo DB / Equilibrium / Reaction Path タブを追加すると **12 タブ** になり、タブバーが画面幅を超える。
**対策**: 左サイドバーに研究フローナビ（既に gate_panel で部分実装）、上タブは「Tier 1 / Tier 2 / Tier 3 / Twin」にグループ化。

#### 限界 2: 1 ファイル app.py が 1,500+ 行

**問題**: ゲート連動 + 平衡計算ボタン + 反応経路レンダリング を追加すると 3,000+ 行になり、保守不可能。
**対策**: Shiny **modularization**（`module_server` / `module_ui`）でタブ別ファイルに分割:

```
src/oscillo_plasma_calc/ui/pages/
├── upload.py
├── waveform.py
├── electrical.py
├── fft.py
├── plasma.py
├── chemistry.py
├── excitation.py
├── thermo_db.py        # NEW
├── equilibrium.py       # NEW
├── reaction_path.py     # NEW
├── trace.py
└── export.py
```

#### 限界 3: 同期処理のみ

**問題**: 平衡計算は数秒、Reaction Path 描画は graphviz 経由で数十秒。同期処理だと UI が固まる。
**対策**: **`shiny.reactive.extended_task`** で非同期化、進捗バー表示。

### 6.2 数値表示の懸念

#### 懸念 1: 桁オーダーが極端な値の表示

平衡組成では mole fraction が 10⁻³⁰ レベルになる。format_si で `1.0×10⁻³⁰` と出すのは正しいが、**「物理的に意味のある桁」の閾値表示** が必要。例:

```
CH3OH: 0.123 (主要)
CO   : 0.045 (主要)
HCO  : 1.2e-8 (微量)
CHO2 : 1.5e-30 (数値ノイズ域、信頼不可)
```

#### 懸念 2: 反応経路図のラベル衝突

ReactionPathDiagram は species 名がノードラベル。30 species 以上だとラベルが重なって読めない。**threshold パラメータで主要経路のみ表示** + **クリックで詳細展開** が標準。

#### 懸念 3: 単位の明示

平衡計算では「Cp [J/mol/K]」「ΔG [kJ/mol]」「mole fraction [dimensionless]」が混在する。**全 KPI 表で単位列を必ず出す**（既に Phase 2 で実装済）。

### 6.3 ユーザー体験の懸念

#### 懸念 1: NASA グレードでも誤用される危険

R²<0.85 の Te でも、ボタンを押せれば計算は走る。Phase 1 で provisional バナーを入れたが、**実際にボタンを disabled にする** 段階までは未実装。

#### 懸念 2: 「結果を信用してよいか」の透明性

CEA-like 自前実装と Cantera の両方で計算して **差分** を出すデュアル検証 UI が必要。差が大きい時は「どちらも信用できない」と表示。

#### 懸念 3: 学生 vs PI のレベル差

3 段階解説で対応しているが、Phase 5+ の熱力学・反応速度は **専門知識の谷が深い**。新配属 B4 が「Gibbs 自由エネルギーって何？」で躓く可能性。**チュートリアルモード**（初回起動時にミニ講義）を追加検討。

---

## 7. 必要なデータ・素材リスト（網羅版）

### 7.1 公開データ（自動取得可能）

| データ | URL | 取得方法 |
|---|---|---|
| NASA Glenn ThermoBuild | https://cearun.grc.nasa.gov/ThermoBuild/ | Web フォーム手動 → CSV 化スクリプト |
| Burcat Database | http://garfield.chem.elte.hu/Burcat/burcat.html | wget で `.dat` |
| GRI-Mech 3.0 | http://combustion.berkeley.edu/gri-mech/ | git clone |
| LXCat 断面積 | https://lxcat.net | API / web 手動 |
| NIST Atomic Spectra DB | https://physics.nist.gov/asd | Web → JSON parse |
| JANAF Tables | https://janaf.nist.gov | Web 手動 |

### 7.2 半公開データ（ライセンス確認要）

| データ | 制約 | 連絡先 |
|---|---|---|
| AramcoMech 2.0 | NUI Galway 非商用 OK | 学術メール OK |
| Konnov mechanism | 公開 | author 直 |
| BOLSIG+ binary | 個人利用 OK、再配布禁止 | LAPLACE 研究所 |

### 7.3 研究室独自データ（手動準備が必要）

⚠ 以下は **私が自動収集できない** もの。野村研究室で手動作業が必須:

1. **野村研の従来実験条件 100+ 例** — オシロ + OES + GC のセット
   - 形式: 各実験を `.csv` x 3 セット + メタデータ `.yaml`
   - 用途: ベンチマーク・検証
2. **触媒系の活性化エネルギー・前指数因子** — 文献値を Excel に集約
   - 形式: `(catalyst, reaction, Ea_kJmol, A_freq, T_range)` のテーブル
   - 用途: Arrhenius 式での反応速度推定
3. **実機の電源仕様書** — 栗田製作所への問合せ結果
   - 形式: `(model, V_max, I_max, PRF_max, pulse_width_min)` 仕様
   - 用途: 装置 1 kW 予算の閾値根拠
4. **GC-MS / HPLC のキャリブレーションファイル** — 各装置の応答係数
   - 用途: 生成物定量の精度向上

### 7.4 合成データ（Phase 5+ で生成）

実装後にコードで作るデータ:

1. **NASA polynomial フィット精度ベンチマーク** — Q(T) 解析解 vs フィット値の誤差マップ
2. **CEA TP/HP/UV 平衡 Pareto front** — SEI vs χ vs η_SE の 3 次元散布図 (50+ 条件)
3. **Reaction Path 既知ベンチマーク** — H2/O2 燃焼（Glassman 教科書例）と比較
4. **EEDF lookup table** — E/N 1-1000 Td x 5 ガス組成 = 5,000 点

---

## 8. 手動で実装する必要のあるタスク

私が **自動で実装できない** タスクを明示:

### 8.1 アクセス権限が必要なもの

- [ ] **GitHub Actions の `workflow` scope 付き PAT で push** — 既に `.github/workflows/test.yml` はローカル作成済、push のみ手動
- [ ] **野村研究室の Google Drive / NAS** から実験データ取得 — 認証が必要
- [ ] **栗田製作所への問合せ** — 電源仕様の正式取得
- [ ] **LXCat アカウント取得** — 断面積データのダウンロード

### 8.2 物理的な実験・測定が必要なもの

- [ ] **タングステン電極で 4 本線同時取得** の実験データ — 林君・芝さんの実機作業
- [ ] **GC-MS の応答係数キャリブレーション** — エタノール標準液 100 ppm
- [ ] **電力計（コンセント側）の実機測定** — 中島先生の購入予定の機材
- [ ] **オシロのプローブ帯域校正** — 高速パルス源と参照セット

### 8.3 ライセンス・倫理・所属組織の判断が必要なもの

- [ ] **論文アーカイブ xlsx の公開可否** — 野村先生の判断
- [ ] **GRI-Mech / Cantera 機構ファイルの再配布** — ライセンス文書の再確認
- [ ] **BOLSIG+ binary 同梱の合法性確認** — LAPLACE 研究所への問合せ
- [ ] **共同研究先（千葉、上越大、東北大）の Citation 同意** — 論文掲載前

### 8.4 専門知識の判断が必要なもの

- [ ] **凝縮相判定の閾値** — 野村研究室での「許容できる過冷却」決定
- [ ] **R² 閾値 0.85 の妥当性** — 過去の論文での慣習との照合
- [ ] **Wilhoit 外挿の T* パラメータ** — species 別の最適値ライブラリ作成
- [ ] **EEDF 二項近似が破綻する閾値** — 野村研究室の経験則

---

## 9. 技術的リスクと緩和策

| リスク | 影響 | 確率 | 緩和策 |
|---|---|---|---|
| Wilhoit フィット失敗 | 高温域 Cp が非物理 | 中 | 失敗検出 + フォールバック (NASA9 の高温区間) |
| Newton-Raphson 発散 | 平衡計算が出ない | 中 | SLSQP フォールバック + 段階的初期化 |
| 凝縮相挿入の振動 | 平衡解が振動 | 低〜中 | ヒステリシス導入 |
| Cantera と CEA-like の差 | 研究者が混乱 | 中 | デュアル表示 + 差分警告 |
| BOLSIG+ M4 Mac 非対応 | Apple ユーザーがフル機能不可 | 高 | bolos Python 実装をフォールバック |
| ReactionPath ラベル衝突 | 30 species で図が読めない | 高 | threshold + クリック詳細 |
| 機構ファイル容量 | 1 MB+ をリポジトリに入れない | 高 | 初回起動時 download |
| 計算時間が UI を固める | 平衡 + 経路で数秒〜数十秒 | 中 | extended_task で非同期化 |
| 学習データ収集の遅延 | NIST/JANAF の Web スクレイピング失敗 | 中 | キャッシュした dump を `data/` に同梱 |
| 実験データ提供の遅延 | 林君・芝さん側の作業待ち | 高 | プレースホルダ合成データで先行開発 |

---

## 10. 段階的ロードマップとマイルストーン

```
M0 (完了、2026-05-02): 土台磨き
  - Phase 0/1/2/3 完了
  - pytest 71 passed
  - Te provisional gate, safe_filename, FFT bug fix

M1 (1 週後): NASA polynomial evaluator
  - thermo/nasa_poly.py: NASA7/9 evaluator
  - 公開 species DB の取り込み（CO2, H2, H2O, CO, CH3OH 等 30 species）
  - tests/test_nasa_poly.py で機械精度一致

M2 (3 週後): TP equilibrium 動作
  - equilibrium/gibbs_minimizer.py: SLSQP 版
  - 凝縮相判定（C(s), CuO 等 10 種）
  - tests/fixtures/cea_examples/ex01-05 で再現性検証
  - UI: Equilibrium タブの最小実装（入力 → mole fraction 表）

M3 (5 週後): Wilhoit + HP/UV equilibrium
  - thermo/wilhoit.py
  - equilibrium で HP, UV 問題タイプ追加
  - 元素ポテンシャル法へ migrate（高速化）

M4 (7 週後): Cantera + Reaction Path
  - thermo/cantera_export.py: YAML 出力
  - UI: Reaction Path タブ（C/H/O 別フラックス図）
  - tests: Cantera と自前実装の差分が < 1 %

M5 (9 週後): BOLSIG+ / LXCat
  - plasma/eedf/bolsig_runner.py + bolos フォールバック
  - LXCat parser + 既定断面積データ同梱
  - UI: Plasma タブの EEDF サブセクション

M6 (10 週後): UI 統合 + 最適化
  - Shiny modularization で app.py を分割
  - extended_task で非同期化
  - チュートリアルモード

M7 (12 週後): 論文補助 + リリース
  - PDF 出力（WeasyPrint）
  - 論文 Methods 節自動生成
  - GitHub Release + Zenodo DOI
```

各 M で **pytest grade A 以上を維持**、できなければ次に進まない。

---

## 11. 結論と推奨アクション

### 11.1 進めるべきか

**はい**、ただし以下を必ず:

1. **データ整備を先行**: 学習データ収集（M0+1 週間）を Phase 5 実装と並行で開始。野村先生・林君・芝さん・千葉さんに連絡。
2. **段階的検証**: M1, M2, ... で必ず pytest を通し、CI を回す。1 段階でも崩れたら次に進まない。
3. **デュアル実装**: 自前 CEA-like と Cantera の両方を持ち、研究者が両者を見比べられる UI に。
4. **手動タスクのトラッキング**: §8 のリストを GitHub Issues に立てて、ボトルネックを可視化。

### 11.2 即着手できるアクション（私が自動で）

- [x] FFT x 軸バグ修正（本日中、commit b868d98 に追加）
- [ ] thermo/ ディレクトリ + species.py スケルトン
- [ ] tests/fixtures/cea_examples/ ディレクトリ + JSON テンプレート
- [ ] requirements.txt に cantera, sympy（既存）, pyyaml（既存）追加
- [ ] docs/ に nasa_polynomial_theory.md（PAC91 理論の Python 実装ガイド）

### 11.3 ユーザー側で着手すべきアクション

- [ ] §8.1 の GitHub `workflow` scope 付き PAT 取得 + `gh auth refresh -s workflow`
- [ ] §8.2 の実験データ取得（タングステン 4 本線、GC-MS キャリブ）
- [ ] §8.3 のライセンス確認（特に xlsx 公開可否）
- [ ] §7.1 の公開データダウンロード（NASA ThermoBuild, Burcat, GRI-Mech）

---

## 付録 A: コード規模見積もり

```
Phase 5 (PAC91)  : +2,500 行（11 式 + species DB + tests）
Phase 6 (CEA)    : +3,500 行（Gibbs minimizer + 凝縮相 + tests）
Phase 7 (Cantera): +1,500 行（YAML export + ReactionPath UI）
Phase 8 (EEDF)   : +2,000 行（BOLSIG runner + LXCat + bolos fallback）
Phase 9 (UI 統合): +2,500 行（modularization + 非同期化 + チュートリアル）
─────────────────────────
合計             : +12,000 行
```

総コード規模は **約 18,500 行**（現在の 6,500 行から 2.8 倍）。研究室レベルとしては大規模だが、CI と pytest で品質維持できれば管理可能。

---

## 付録 B: 参考文献

- Gordon, S., McBride, B. J. (1996) "Computer Program for Calculation of Complex Chemical Equilibrium Compositions and Applications" NASA RP-1311
- McBride, B. J., Gordon, S. (1992) "Computer Program for Calculating and Fitting Thermodynamic Functions" NASA RP-1271
- Hagelaar, G. J. M., Pitchford, L. C. (2005) "Solving the Boltzmann equation to obtain electron transport coefficients and rate coefficients for fluid models" PSST 14:722 (BOLSIG+ 原典)
- Goodwin, D. G., Moffat, H. K., Speth, R. L. (2009) Cantera (現バージョン 3.2)
- Snoeckx, R., Bogaerts, A. (2017) "Plasma technology – a novel solution for CO₂ conversion?" Chem Soc Rev 46:5805
- Fridman, A. (2008) "Plasma Chemistry" Cambridge Univ. Press

---

*本レポートは 2026-05-02 時点の実装状況・コードベース・スクショ分析に基づく。Phase 5 着手前の合意形成資料として使用する。次回更新は Phase 5 M1 完了時を予定。*
