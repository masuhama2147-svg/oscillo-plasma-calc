# 高次理論式追加 & Trace タブ UX 最適化 実装プラン

**発端**: ユーザ依頼（2026-04-23）
- 「Peak instantaneous power |P|_max を時間で割った値を計測したい」= ピーク電力ベースの平均換算・装置全体 **1 kW 以下** の安全運用チェック
- Trace タブが「情報量多くて見づらい」= 最初は必要最低限に、漸進開示
- 博士油合成研究者として **新たな理論式を多角的に考察・実装**
- すべて自動で実装（auto モード）

---

## §1. 新規追加する理論式（油合成研究者視点の徹底考察）

### 1.1 ピーク電力ベースの平均電力と 1 パルスエネルギー分解

現在 P̄ は **観測窓 T** の時間平均。しかし観測窓には複数パルスが含まれうるため、**パルス単位の物理量** を分離して評価する価値が大きい。

| # | 量 | 式 | 意味 |
|---|---|---|---|
| A-1 | パルスエネルギー E_pulse | $E / N_\mathrm{pulses}$ | 1 発のパルスが反応器に入れるエネルギー（窓平均でなく） |
| A-2 | パルス平均電力 P̄_pulse | $E_\mathrm{pulse} / \tau_\mathrm{pulse}$ | パルス持続時間 τ_pulse = FWHM で割ったピーク領域の平均電力 |
| A-3 | ピーク電力時間平均換算 P_eff | $P_\mathrm{peak} \cdot D$ | ピーク電力 × デューティ比。装置全体への平均負荷（1 kW 制約チェックに直結）|
| A-4 | 絶対値時間平均 ⟨\|P\|⟩ | $\frac{1}{T}\int \|V\,I\|\,dt$ | 変位電流成分も含めた「実効的な」入力平均。P̄ との差が誘導/容量性損失の尺度 |

### 1.2 信号形状指標（パルスの鋭さ）

| # | 量 | 式 | 意味 |
|---|---|---|---|
| A-5 | Crest factor CF | $V_\mathrm{peak}/V_\mathrm{rms}$ | ピーク/実効値比。正弦波 CF=√2=1.41、パルス CF は √(1/D)、本データで ≈ 9 |
| A-6 | Form factor FF | $V_\mathrm{rms}/\|V\|_\mathrm{avg}$ | 正弦波 FF=π/(2√2)=1.11、ピーク性が強いほど大 |
| A-7 | Duty cycle D | $\tau_\mathrm{pulse}/T_\mathrm{PRF}$ | 1 周期あたりパルスがオンの時間割合。D と V_rms から検証可能 |
| A-8 | パルス数 N_pulses | 観測窓内のピーク検出数 | `scipy.signal.find_peaks` |

### 1.3 電力密度（反応器設計の核）

| # | 量 | 式 | 意味 |
|---|---|---|---|
| A-9 | プラズマ電力密度 p_vol | $\bar{P}/V_\mathrm{plasma}$ | 単位プラズマ体積あたりの投入電力。W/m³ |
| A-10 | プラズマエネルギー密度 e_vol | $E_\mathrm{pulse}/V_\mathrm{plasma}$ | 1 パルスあたりの体積密度 J/m³ |

V_plasma はユーザ入力（電極ギャップ × 電極断面積）で得る。

### 1.4 油合成特有の KPI（博士レベル）

液中プラズマ CO₂ 還元 → 液体燃料研究で **実用指標** として必須。

| # | 量 | 式 | 意味 | 根拠 |
|---|---|---|---|---|
| B-1 | 比エネルギー投入量 SEI | $E_\mathrm{plasma}/n_{\mathrm{CO}_2}$ | kJ/mol、CO₂ プラズマ化学の universal 指標 | Snoeckx & Bogaerts 2017 ChemSocRev 46:5805 |
| B-2 | エネルギーコスト EC | $E_\mathrm{plasma}/n_\mathrm{prod}$ | 目的物 1 mol あたりの投入エネルギー | Bogaerts 2018 JPD 51:144002 |
| B-3 | CO₂ 変換率 χ_CO2 | $(n_\mathrm{in}-n_\mathrm{out})/n_\mathrm{in}$ | 入力 CO₂ の何 % が反応したか | 同上 |
| B-4 | 単位エネルギー変換率 η_SE | $\chi \cdot \Delta H_r / \mathrm{SEI}$ | エネルギー換算効率（η_chem の別表現） | 同上 |
| B-5 | Anderson-Schulz-Flory 連鎖確率 α_ASF | 炭化水素分布から回帰 | Fischer-Tropsch 油合成で重要 | ASF 原理 |
| B-6 | C1 選択性 vs C2+ 選択性 | 生成物群別分率 | 油化への適性 | — |

### 1.5 プラズマ非平衡診断（博士レベル）

| # | 量 | 式 | 意味 | 根拠 |
|---|---|---|---|---|
| C-1 | 換算電場 E/N | $E_\mathrm{field}/n_\mathrm{gas}$ [Td] | 電子エネルギー分布を決める第一パラメータ | Bolsig+ 慣行 |
| C-2 | 電子平均エネルギー ⟨ε⟩ | E/N 依存の関数 | CO₂ 電離・解離断面積ピーク 13 eV との比較 | Phelps LXCat |
| C-3 | 回転温度 T_rot | OH (A–X) or N₂ (C–B) バンド形状フィット | ガス温度 T_gas の実測プロキシ | Bruggeman 2014 PSST |
| C-4 | 振動温度 T_vib | CO₂ asymmetric stretch or N₂ Δv=2 強度比 | CO₂ 還元効率の駆動量 | Fridman 2008 Plasma Chemistry |
| C-5 | 非平衡度 T_e / T_gas | 診断 Te と T_rot の比 | 100 以上 ⇔ 強い非平衡 = CO₂ 還元に有利 | 同上 |
| C-6 | Druyvesteyn 分布ピーク | EEDF のピーク位置（E/N から推定） | 電子衝突断面積ピーク到達度 | Fridman 2008 |

### 1.6 装置運用・安全指標（ユーザ最重要要望）

**装置全体 1 kW 以下** の制約を満たすための監視機構。

| # | 量 | 式 | 意味 | 判定 |
|---|---|---|---|---|
| D-1 | 装置全体電力予算 W_budget | 設定値（既定 1000 W） | 研究室運用上限 | — |
| D-2 | 推定平均電力 P_est | $P_\mathrm{peak} \cdot D$ or P̄ | 装置が実際にまわっている平均電力 | — |
| D-3 | 予算余裕度 M_budget | $(W_\mathrm{budget} - P_\mathrm{est})/W_\mathrm{budget}$ | > 0 なら OK、< 0 なら超過 | **< 0 で赤エラー** |
| D-4 | 冷却必要量 Q_cool | $P_\mathrm{est} - P_\mathrm{chem}$ | 化学エネルギーに変換されずに熱になる分 | 設備設計 |
| D-5 | プラズマ利用率 η_dev | $\bar{P}_\mathrm{plasma}/W_\mathrm{socket}$ | コンセント側に対する放電側の割合 | 会議議事録 2026-04-23 |

### 1.7 波形の信号品質（統計）

| # | 量 | 式 | 意味 |
|---|---|---|---|
| E-1 | Signal-to-Noise 比 S/N | $V_\mathrm{peak}^2 / \sigma_\mathrm{baseline}^2$ | プレトリガ区間の分散をノイズ基準に |
| E-2 | パルス間ジッタ σ_t | 連続パルスの立ち上がり時刻の std | トリガ精度指標 |
| E-3 | パルス間エネルギー CV | E_pulse の変動係数 | 放電の再現性指標 |

---

## §2. Trace タブ UX の再設計

### 2.1 現状の問題（スクショ確認）

- カードが全展開（⬇）になっており、1 画面に **2〜3 個** しか入らない
- 20+ の物理量を順に見るのに **過度なスクロール**
- 初学者解説が最初から展開されているため **研究者には冗長**
- 警告や異常に **視覚的優先順位** がない（探さないと見えない）

### 2.2 新設計 — 漸進開示 (Progressive Disclosure)

```
┌──────────────────────────────────────────────────────────────────┐
│ 📊 解析サマリ                                                     │
│ 計算済み: 20 物理量  |  ✓正常: 15  |  ⚠警告: 4  |  ✗異常: 0   │
│ 🔌 装置予算 1000 W に対して 推定平均 856 W → 余裕 14 %          │
│                                                                   │
│ [ フィルタ: ●全部  ○ 警告のみ  ○ 異常のみ ]                    │
│ [ 展開: 全部畳む | 全部開く | 解説のみ | 式のみ ]              │
└──────────────────────────────────────────────────────────────────┘

━━━ 📐 電気系 (Tier 1) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ (12) ▾
┌──────────────────────────────────────────────────────────────────┐
│ ▶ Peak-to-peak voltage Vpp                  ⓘ         11.84 kV │ ← 閉
├──────────────────────────────────────────────────────────────────┤
│ ▶ Peak-to-peak current Ipp                  ✓           56.0 A │
├──────────────────────────────────────────────────────────────────┤
│ ▶ Rise time t_r                             ⚠        2.43 μs   │
├──────────────────────────────────────────────────────────────────┤
│ ▶ Peak instantaneous power                  ✓        145.1 kW  │
├──────────────────────────────────────────────────────────────────┤
│ ▶ Estimated average power (Ppeak·D)        ✓           1.70 W  │
...

━━━ 🔬 油合成 KPI ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ (4) ▾
...

━━━ 🌡️ プラズマ診断 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ (6) ▾
...

━━━ 🔌 装置運用 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ (4) ▾
┌──────────────────────────────────────────────────────────────────┐
│ ▶ 装置予算残量                              ✓          14.4%   │
└──────────────────────────────────────────────────────────────────┘
```

### 2.3 カード詳細（クリックで展開）

クリックで 3 段階の展開:
- **Level 1**（デフォルト・閉じた状態）: 名前 + 値 + バッジのみ
- **Level 2**（クリック 1 回）: 🔰 初学者解説 + 理論式 1 行
- **Level 3**（「🔬 詳細を見る」クリック）: 研究者解説 + 博士解説 + 中間ステップ + エラーライン詳細

### 2.4 実装仕様

- カードは **`<details>` デフォルト閉** に変更
- カテゴリ見出しは展開可能、バッジでカウント表示
- サマリヘッダは **sticky position** で常時見える
- フィルタはクライアントサイド JS（カテゴリ `data-*` 属性で表示切替）
- カラーブラインド配慮: アイコン（✓/⚠/✗）を色と並記

---

## §3. 新規モジュール

```
src/oscillo_plasma_calc/
├── electrical/
│   └── advanced.py          # NEW: pulse energy, crest/form factor, duty, power density, |P| avg
├── chemistry/
│   └── oil_synthesis.py     # NEW: SEI, EC, χ_CO2, η_SE
├── plasma/
│   └── nonequilibrium.py    # NEW: E/N, mean energy, T_rot, T_vib, non-eq ratio
├── qa/
│   └── operational.py       # NEW: device budget check, 1 kW rule
├── docs/
│   ├── explanations.py      # UPDATED: +20 新物理量の 3 レベル解説
│   └── typical_ranges.py    # UPDATED: +20 新物理量の典型範囲
├── pipeline.py              # UPDATED: 新量を AnalysisBundle に統合
└── ui/
    └── app.py               # UPDATED: Trace タブ 完全刷新 (compact + category + filter)
```

---

## §4. 実装 Phase

| Phase | 内容 | 所要 |
|---|---|---|
| A | `electrical/advanced.py` 実装（A-1〜A-10）+ pipeline 統合 | 中 |
| B | `chemistry/oil_synthesis.py` 実装（B-1〜B-4）+ Chemistry タブ拡張 | 中 |
| C | `plasma/nonequilibrium.py` 実装（C-1〜C-5）+ Plasma タブ拡張 | 中 |
| D | `qa/operational.py` 実装（D-1〜D-5）+ Upload / Electrical 統合 | 低 |
| E | `docs/` 追補（新 20 量の explanation + range） | 低 |
| F | **Trace タブ完全刷新**（Phase A-E の出力を compact card で表示、カテゴリ、フィルタ、統計ヘッダ） | 高 |
| G | pytest 追加（新量の数値検証） | 低 |
| H | ブラウザ検証（Upload → Trace、警告が正しく色付けされるか） | 低 |

---

## §5. 根拠論文（最新・参照元）

### 油合成・CO₂ プラズマ化学
- Snoeckx, R. & Bogaerts, A. (2017) "Plasma technology – a novel solution for CO₂ conversion?" *Chem. Soc. Rev.* **46**: 5805. — SEI の標準的定義
- Bogaerts, A. & Neyts, E. C. (2018) "Plasma Technology: An Emerging Technology for Energy Storage" *ACS Energy Lett.* **3**: 1013.
- van Rooij, G. et al. (2017) "CO₂ dissociation by RF plasma" *Plasma Proc. Polym.* **14**: e1600082.
- Fridman, A. (2008) *Plasma Chemistry*. Cambridge University Press. — 非熱平衡理論

### 電力計測（変位電流分離など）
- Peeters, F. J. J. & van der Laan, I. (2015) "The influence of partial discharge on DBD power measurement" *PSST* **24**: 015014. — 変位電流除去
- Manley, T. C. (1943) "The electric characteristics of the OZ discharge" *Trans. Electrochem. Soc.* **84**: 83. — Lissajous 古典

### 液中プラズマ診断
- Bruggeman, P. J. et al. (2014) "Plasma-liquid interactions: a review and roadmap" *PSST* **23**: 045022.
- Gigosos, M. A. & Cardeñoso, V. (1996) "New plasma diagnosis tables of hydrogen Stark broadening" *J. Phys. B* **29**: 4795.
- Seepersad, Y. et al. (2013) "Electron kinetics in nanosecond-pulsed discharge in liquid water" *J. Phys. D* **46**: 355201.

### Fischer-Tropsch / ASF 油合成
- Anderson, J. R. (1984) *The Fischer-Tropsch Synthesis*. Academic Press.

### 野村研究室内
- 2006_JJAP-45-8864 / 2009_JAP-106-113302 / 2009_POP-16-033503 / 2011_PSST-20-034016 / 2013_CAP-13-1050 / 2017_JEPE-10-335 / 2020_JJIE_99-104

---

## §6. 検証計画

### A. 理論整合性（研究者視点）
- Ppeak × Duty ≈ P_eff の一貫性
- SEI = E/n_CO2 が文献値 ~3-10 eV/molecule = 300-1000 kJ/mol レンジに入るか
- Crest factor が 1/√D 理論値と一致
- E/N が Td 単位で 100-1000 の典型範囲
- η_dev = P̄ / W_socket が 60-90 % の範囲（会議議事録と整合）

### B. pytest
- `test_advanced_electrical.py`: pulse_energy, crest_factor, form_factor, duty_cycle
- `test_oil_synthesis.py`: SEI, EC, χ_CO2
- `test_nonequilibrium.py`: E/N 計算、T_rot/T_vib のスタブ
- `test_operational.py`: budget check が警告を正しく出すか

### C. ブラウザ検証
- Trace タブがカテゴリで分かれて、初期は全閉
- 警告カードが上位に集まって見える（フィルタ使用時）
- 統計ヘッダが sticky で常時見える

---

## §7. 成果物（完成後の体験）

1. Upload 後の Trace タブは **1 画面にほぼ収まる** コンパクト表示
2. ⚠ 警告と ✗ 異常が **スクロール無しで発見** できる（フィルタ 1 クリック）
3. 装置全体 **1 kW 制約** に対する余裕度が常に見える
4. 博士レベルの研究者には SEI / EC / E/N / T_vib など油合成固有指標が即座に得られる
5. 新配属 B4 には カードをクリックすれば初学者解説が出る、という **同じ UI で両方の使い方** が成立

この「階層的情報密度」設計が、本改修のコアバリュー。
