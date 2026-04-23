# 油合成研究者向け UX 再設計 実装プラン

**対象ユーザー**: 野村研究室の液中プラズマ CO₂ 還元 → 液体燃料（油合成）研究者。
学部 4 年生（研究室新配属）から博士・PI まで、スキル幅広。

**目的**:
1. **CSV をアップロードするだけ** で解析が走る状態にする（現在は path 欄へのタイプ入力）
2. アップロード前に **CSV 形式仕様** を UI 上で明示、フォーマット違反を即エラー表示
3. 各計算結果に **「エラーライン」**（期待範囲からの逸脱警告）を付け、逸脱時は **「何が原因か・どの論文を見るか」** まで誘導
4. 表・図の **見方を初心者向けに解説**
5. Trace タブの各式に **3 レベル（初学者 / 研究者 / 博士）の解説トグル** を実装、使い方・理想値・引用論文まで明示
6. UI/UX は **HCI / 人間工学の知見** に沿った設計（Nielsen 10 heuristics + 科学ダッシュボード研究）

---

## 1. UX 設計原則（採用する枠組み）

### 1.1 Nielsen 10 ヒューリスティクス（1994, 現在も基準）

本プロジェクトで特に重視するのは:

| # | 原則 | 本アプリでの適用 |
|---|---|---|
| 1 | 状態の可視化 (Visibility of system status) | アップロード中・計算中・警告発生をバッジと色で即時提示 |
| 2 | 実世界とシステムの一致 | 油合成・プラズマ研究者の既存語彙で UI ラベル（「パルス幅」「Vpp」等）|
| 3 | ユーザのコントロール | 複数条件を比較できる、前の波形に戻れる |
| 5 | エラー防止 | CSV 形式逸脱をアップロード前の仕様表示＋即時バリデーションで防ぐ |
| 6 | 想起より認識 | 「どのファイルをどこに入れるか」は UI に常時表示 |
| 9 | エラーの認識・診断・回復 | 「エラーライン」：異常値 + 原因候補 + 引用論文をその場で表示 |
| 10 | ヘルプとドキュメンテーション | 各タブに折りたたみ式のガイドを常設 |

### 1.2 科学ダッシュボード研究からの知見（2020〜）

- **Munzner (2014) "Visualization Analysis and Design"**
  - *Effectiveness* > *Expressiveness*：必要な情報を **最小の認知負荷** で伝える
- **Sarikaya & Gleicher (2018) "Design Factors for Summary Visualization in Visual Analytics"** (IEEE TVCG)
  - Dashboard は **"Overview → Filter → Detail on demand"** が最も認知負荷低
  - 本アプリに適用: Upload（Overview）→ 各タブ（Filter）→ Trace カード展開（Detail）
- **Midway (2020) "Principles of Effective Data Visualization"** (Patterns)
  - **色は意味に使う**（赤 = 警告、緑 = 正常、青 = 情報）
- **Cognitive Load Theory (Sweller et al.)**
  - "Intrinsic（内在的）/ Extraneous（外在的）/ Germane（有益な）" の切り分け
  - UI 装飾（extraneous）を減らし、**研究者の判断を助ける情報**（germane）を手前に出す

### 1.3 多層解説（Progressive Disclosure）

Trace カードに 3 レベルのトグル:

```
┌─── カード ───────────────────────────────────┐
│ 物理量名                          大きな数値  │
├── ▾ 初学者向け（何を測っている？）──────────│
│   Vpp はパルス電圧の「振れ幅」。             │
│   プラズマの強さを表す最も基本の指標です。   │
│   数値が大きいほど強いパルスが入っています。│
├── ▾ 研究者向け（使い方・理想値・見どころ）──│
│   液中ストリーマ放電では 5〜12 kV が典型。   │
│   今回の値: 11.84 kV → 最大強度条件。        │
│   Paschen 電圧を大きく超え、ブレークダウン   │
│   確定。Ipp とセットで確認。                 │
├── ▾ 博士向け（深掘り・誤差論・論文リンク）─│
│   プローブ帯域 >> 1/τ_rise であることを確認。│
│   Vpp 誤差は主に DC オフセットで、中心合わせ │
│   で ±2% 以内に収まる。2013_CAP-13-1050 と   │
│   整合（典型 3〜15 kV バンド）。             │
├── ▾ 理論式（展開）─────────────────────────│
│   Vpp = Vmax − Vmin                          │
│   Vpp = 3.68 kV − (−3.12 kV) = 6.8 kV        │
├── ▾ エラーライン判定 ─────────────────────│
│   ✓ 正常（典型範囲 5〜12 kV 内）              │
│     もし範囲外なら「プローブ校正要確認」等   │
└──────────────────────────────────────────────┘
```

**なぜこの順序**: 研究者が **まず結果を見て → その意味を解釈 → 詳細調査** というフローを取るため。博士レベルが一番下なのは、初学者が冒頭で混乱しないため（研究室の OJT フレンドリー）。

### 1.4 エラー防止のレイヤ設計

```
レイヤ 1: 入力前  — 許可形式を UI 上で常時表示（サンプル CSV も）
レイヤ 2: 入力時  — ファイル選択直後にヘッダ・列数・単位をバリデート
レイヤ 3: 計算時  — 物理量計算ごとに「期待範囲」と突き合わせ、外れたら警告
レイヤ 4: 解釈時  — 警告には「原因候補」と「参照論文」を付けて誘導
```

---

## 2. Upload タブ 再設計

### 2.1 現状の問題

- CSV アップロードが **pathテキスト入力** のみ（ドラッグ＆ドロップ不可、誤タイプで詰む）
- 受け付ける CSV の形式が **どこにも書かれていない**
- 誤フォーマットを入れたときのエラーが不親切

### 2.2 新 Upload タブの構成

```
┌────────────────────────────────────────────┐
│ STEP 1  CSV を準備する                      │
│ ───────────────────────────────────────── │
│ 【受け付ける形式】（以下 3 列必須、SI 単位）│
│                                             │
│   time_s,     voltage_V,   current_A        │
│   -2.000e-5,  -120.0,      0.02             │
│   -1.999e-5,  -118.0,      0.01             │
│   ...                                       │
│                                             │
│ ▾ 詳しい仕様と例（展開）                   │
│   - 先頭 `#` 行はメタデータ (key=value 形式)│
│   - 時間は SI 秒（負値可、オシロの時間基準）│
│   - 電圧は V、電流は A（プローブ校正済み）  │
│   - 行数上限: 100,000（それ以上はダウンサンプル）│
│   - Δt は一定間隔が推奨                      │
│                                             │
│ [📋 テンプレート CSV をダウンロード]         │
├────────────────────────────────────────────┤
│ STEP 2  ファイルをアップロード              │
│ ───────────────────────────────────────── │
│ [ ドラッグ & ドロップ / クリックで選択 ]    │
│                                             │
│ 選択中: ( まだありません )                  │
├────────────────────────────────────────────┤
│ STEP 3  読み込んで計算                      │
│                                             │
│   パルス繰返し周波数 f [Hz]: [10000]       │
│   ( 既定: 観測窓 = 1 周期 )                │
│                                             │
│   [ 読み込む ]                              │
└────────────────────────────────────────────┘
```

右側パネル（データ読み込み後）:

```
┌── ✓ 読み込み成功 ────────────────────────┐
│ ファイル: PW_1p50.csv                       │
│ N = 10,000 サンプル / Δt = 2.000 ns         │
│ 測定期間 = 19.998 μs                        │
│ Vpp = 11,840 V (11.84 kV)                   │
│ Ipp = 56.0 A                                │
├── ⚠ バリデーション結果 ──────────────────┤
│ ✓ 時間軸が単調増加                         │
│ ✓ Δt のばらつき < 1 %                      │
│ ! 先頭 10 サンプルの DC オフセット 3.2 V   │
│   → 前処理で中心合わせを推奨               │
│ ✓ Vpp = 11.8 kV → ストリーマ放電帯域内     │
├── 次にすること ────────────────────────── │
│ → Waveform タブで波形を確認                │
│ → Electrical タブで電力・エネルギーを計算  │
│ → Trace タブで途中式とエラーラインを確認   │
└──────────────────────────────────────────┘
```

### 2.3 失敗ケースの表示例

```
┌── ✗ 形式エラー ──────────────────────────┐
│ ファイル: broken.csv                        │
│                                             │
│ 問題: 列 'voltage_V' が見つかりません       │
│ 実際の列: ['time', 'V', 'I']               │
│                                             │
│ 💡 対処: 列名を以下に修正してください       │
│   time → time_s                             │
│   V    → voltage_V                          │
│   I    → current_A                          │
│                                             │
│   STEP 1 の形式例を参考にしてください       │
└──────────────────────────────────────────┘
```

### 2.4 技術実装

- `shiny.ui.input_file()` を使用（既に励起温度タブで実装経験あり）
- 受け付け直後にバリデータを走らせ、**3 層の通知**:
  1. ハードエラー（列不足等）→ 赤、計算不可
  2. ソフトウォーニング（Δt ばらつき等）→ 黄、計算可だが要確認
  3. OK 情報 → 緑、そのまま続行

---

## 3. エラーライン（各物理量の異常値検出）

### 3.1 典型範囲の根拠（野村研究室論文アーカイブから引用）

| 物理量 | 典型範囲 | 範囲外時の可能性（原因） | 参照論文 ID |
|---|---|---|---|
| Vpp | 3 – 15 kV | < 1 kV: 電源出力不足 / プローブ分圧誤校正<br>> 20 kV: プローブ入力オーバー / ダメージ | 2013_CAP-13-1050 |
| Ipp | 10 – 100 A | < 1 A: 放電未点弧（絶縁破壊未達）<br>> 200 A: 短絡疑い / 電流プローブ飽和 | 2011_PSST-20-034016 |
| Rise time (ns パルス) | 1 – 500 ns | > 1 μs: プローブ帯域不足 / パルス整形回路劣化<br>< 0.5 ns: サンプリング不足（Δt 制約） | 2013_CAP-13-1050 |
| dV/dt | 10⁹ – 10¹² V/s | < 10⁸: DC 成分しか無い / トリガ失敗<br>> 10¹³: ノイズスパイク検出 | 2013_CAP-13-1050 |
| Pピーク | 1 kW – 1 MW | < 100 W: V と I が逆相 / 接続問題<br>> 10 MW: プローブ飽和 | 2006_JJAP-45-8864 |
| E（観測窓） | 0.1 mJ – 100 mJ | < 0.01 mJ: 放電無し / 観測窓外<br>> 1 J: 時間軸単位の誤認識 | 2008_APEX-1-046002 |
| P̄（観測窓） | 10 W – 1 kW | 観測窓 ≠ 1 周期 の場合を要確認 | 2008_APEX-1-046002 |
| Vrms | Vpp × 0.05 – 0.5 | Vrms/Vpp 比からデューティを推定、想定から外れたら要確認 | — |
| Te（Boltzmann 2 本線） | 0.5 – 5 eV | < 0.3 eV: LTE 未成立 / 線強度比不正<br>> 10 eV: 自己吸収無視の誤用 | 2006_JJAP-45-8864 |
| Te（Boltzmann plot n 本） | 5,000 – 30,000 K | < 3,000 K: 線選択不良（E_u 差が小さい）<br>負値: slope 符号反転（除外線の再検討）| 2006_JJAP-45-8864, 2009_JAP-106-113302 |
| ne（Stark） | 10²¹ – 10²⁴ m⁻³ | α(Te) 未補正で誤差大 | 2009_POP-16-033503 |
| G 値 | 0.5 – 20 molecules/100 eV | < 0.1: エネルギー効率悪化<br>> 50: 触媒効果 or 測定誤り | 2012_IJHE-37-16000 |
| η_chem | 1 – 20 % | < 0.5 %: 反応器設計見直し<br>> 30 %: 典型を超える、再現性確認 | 2017_JEPE-10-335 |

この表を `docs/explanations.py` と同居する **`typical_ranges.py`** として実装、各 compute 関数や UI が参照する。

### 3.2 エラーライン表示の仕様

```
status    色    アイコン   文言例
─────────────────────────────────
OK        #1a7  ✓         典型範囲（3〜15 kV）内
NOTICE    #38a  ℹ         範囲の端。電源設定を確認推奨
WARNING   #c80  ⚠         範囲外。可能原因: プローブ帯域不足
ERROR     #c33  ✗         測定失敗の可能性高い。再測定を推奨
```

判定は **連続値** で持ち、境界値付近では「NOTICE」に落とすことで過剰警告を抑える。

---

## 4. タブ別の初心者ガイド

各タブの上部（or サイドバー）に折りたたみパネルを設置、初学者向けの「このタブで何ができるか」を 3〜5 行で解説。研究者にとっては閉じればよいだけ（認知的負担ゼロ）。

### Waveform タブ

```
▾ このタブの読み方
  青線 V(t): 電極に印加した電圧波形。
  赤線 I(t): 放電で流れた電流波形。
  横軸は μs。マウスドラッグで拡大可能。
  【見どころ】立ち上がり瞬間（エッジ）では V と I がほぼ同時に立つ
             ⇔ 抵抗性負荷、時間差がある ⇔ 誘導性／容量性成分あり
```

### Electrical タブ

```
▾ このタブの読み方
  表: Vpp, Ipp, 平均電力、実効値などをまとめて表示。
  P(t) プロット: 各時刻の瞬時電力。ピークが鋭く立つ ⇔ パルス放電成立。
  Lissajous プロット: V-q 平面。閉ループの面積 = 1 周期エネルギー。
  【注意】P̄ は「観測窓」の時間平均。PRF と窓長の関係に留意。
```

### FFT タブ

```
▾ このタブの読み方
  V / I の周波数スペクトル（両対数軸）。
  ピーク周波数 = 駆動源（RF 27 MHz、MW 2.45 GHz 等）。
  高調波 (2f, 3f...) の強度比で非線形性（プラズマ形成度）を見る。
  【注意】Nyquist = f_s / 2 = 250 MHz を超える成分は信用しない。
```

### Plasma タブ

```
▾ このタブの読み方
  左：発光分光から Te, ne を推定する入力欄。
  入力値は OES 測定（分光器）からの強度比・線幅。
  【典型】Te = 0.5〜5 eV、ne = 10²¹〜10²⁴ m⁻³。
  【注意】Paschen 式は気相向け。液中は経験補正が別途必要。
```

### Chemistry タブ

```
▾ このタブの読み方
  GC 分析で得た生成モル数 × ΔH で化学効率 η を算出。
  G 値は「100 eV あたり何分子作れたか」の普遍指標。
  【典型】η = 5〜15 %、G = 1〜10 molecules/100 eV。
  【注意】n_prod は目的生成物のみ。副生成物は選択性で別途評価。
```

### 励起温度 Te タブ

```
▾ このタブの読み方
  元素を選ぶ → その元素のスペクトル線強度を入力 → Boltzmann plot で Te 推定。
  強度 0 の線は自動で除外（xlsx と同じ挙動）。
  【使うべき線の本数】3 本以上推奨。2 本だと誤差が大。
  【注意】同一電離段階・同一元素・異なる上準位エネルギーで揃えること。
```

### Trace タブ

```
▾ このタブの読み方
  各物理量の式と数値代入を順に表示。
  各カードは「初学者 → 研究者 → 博士」の 3 レベル解説が折りたたまれている。
  エラーライン（異常値検出）の結果もこのタブに反映。
```

---

## 5. Trace タブ カード構造（最終形）

```
┌─── ピーク間電圧 Vpp ────────────────────── 11.84 kV ✓ ───┐
│                                                          │
│ ▾ 🔰 初学者向け                                           │
│   Vpp は「電圧の振れ幅」です。放電の強さを表します。     │
│   値が大きいほど強いパルスが電極にかかっています。       │
│                                                          │
│ ▾ 🔬 研究者向け                                           │
│   液中ストリーマ放電の典型値: 3〜15 kV                   │
│   今回の値 11.84 kV は上位帯域 → CO₂ 電離効率が高い候補 │
│   Ipp とセットで確認：Vpp × Ipp ≈ Ppeak オーダー            │
│                                                          │
│ ▾ 🎓 博士向け                                             │
│   プローブ帯域 BW ≫ 1/τ_rise であることを確認。          │
│   DC オフセット補正後の Vpp 誤差は ±2 % 以内。            │
│   ref: 2013_CAP-13-1050（ns-pulse breakdown 帯域 3-15 kV）│
│                                                          │
│ ▾ 理論式                                                 │
│   Vpp = Vmax − Vmin                                      │
│   Vpp = 3.68 kV − (−3.12 kV) = 6.80 kV                   │
│                                                          │
│ ▾ エラーライン判定                                       │
│   ✓ 正常（3〜15 kV の典型範囲内）                         │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

3 レベル解説の分担:

| レベル | 対象 | 内容 | 長さ |
|---|---|---|---|
| 🔰 初学者 | 学部 4 年生 / 新配属学生 | 何を測っているか（日常語） | 2〜3 行 |
| 🔬 研究者 | M1〜PD / 中堅 | 典型値と見方、他量との関係 | 3〜5 行 |
| 🎓 博士 | PI / 査読対応 | 誤差論・前提・引用論文 | 4〜7 行 |

---

## 6. 実装アーキテクチャ

### 6.1 新規モジュール

```
src/oscillo_plasma_calc/
├── docs/                          # NEW
│   ├── __init__.py
│   ├── explanations.py            # 物理量ごとの 3 レベル解説テキスト
│   └── typical_ranges.py          # 典型範囲とエラーライン判定
├── qa/                            # NEW
│   ├── __init__.py
│   ├── csv_validator.py           # CSV 形式バリデータ（列・型・Δt・単調性）
│   └── anomaly.py                 # 計算結果の典型範囲チェック
```

### 6.2 データ構造

```python
# docs/explanations.py
@dataclass
class ExplanationSet:
    key: str                # "vpp", "mean_power", ...
    beginner: str
    researcher: str
    phd: str
    references: list[str]

# docs/typical_ranges.py
@dataclass
class TypicalRange:
    key: str
    low: float
    high: float
    unit: str
    below_low_causes: list[str]        # 下抜けの原因候補
    above_high_causes: list[str]       # 上抜けの原因候補
    references: list[str]

# qa/anomaly.py
@dataclass
class AnomalyCheck:
    level: str                          # "ok" | "notice" | "warning" | "error"
    message: str
    causes: list[str]                   # 原因候補
    references: list[str]               # 引用論文
```

各 `TraceResult` に:
- `explanation: ExplanationSet | None`
- `anomaly: AnomalyCheck | None`
を attach。`trace_to_html` が開口部に 3 レベル解説 + 判定を展開する。

### 6.3 UI 変更点

- `ui/app.py::trace_to_html()` を 3 レベル対応に拡張
- `ui/app.py::app_ui` の **Upload タブ** を step-wise レイアウトに書き換え
- `input_text("csv_path", ...)` を **`input_file("csv_upload", accept=['.csv'])`** に置換
- 各タブ上部に折りたたみガイドを追加

### 6.4 pytest

- `tests/test_validation.py`: 正常 CSV、列名欠損、Δt 不均一、DC オフセット検出
- `tests/test_anomaly.py`: 各物理量の閾値判定テスト
- `tests/test_explanations.py`: 全 20+ 物理量に 3 レベル解説が揃っているか

---

## 7. 実装フェーズ

### Phase 1 — エラー防止の基盤（今回実装）
1. `docs/explanations.py` に全物理量の 3 レベル解説を記述（最重要）
2. `docs/typical_ranges.py` で典型範囲 DB 作成
3. `qa/csv_validator.py` で CSV バリデータ
4. `qa/anomaly.py` で計算結果の閾値判定
5. 既存 `TraceResult` に `explanation` と `anomaly` フィールド追加
6. `pipeline.analyze_electrical` で自動的に anomaly 判定を付加

### Phase 2 — UI 面（今回実装）
7. Upload タブを step-wise レイアウトに変更、`input_file` で CSV アップロード
8. 各タブ上部に「読み方ガイド」折りたたみ
9. Trace カードを 3 レベル解説対応
10. Electrical タブのサマリ表にエラーライン色分けを追加

### Phase 3 — 将来拡張（今回はプランのみ）
11. 「2 条件を並べて比較」モード
12. 「過去の測定との比較」（ローカル履歴 DB）
13. 実測波形の前処理自動提案（オフセット除去・スムージング推奨）
14. PDF エクスポート + ヘッダに研究室ロゴ

---

## 8. Critical Files（実装で触る主要ファイル）

- 新規作成:
  - `src/oscillo_plasma_calc/docs/__init__.py`
  - `src/oscillo_plasma_calc/docs/explanations.py`
  - `src/oscillo_plasma_calc/docs/typical_ranges.py`
  - `src/oscillo_plasma_calc/qa/__init__.py`
  - `src/oscillo_plasma_calc/qa/csv_validator.py`
  - `src/oscillo_plasma_calc/qa/anomaly.py`
  - `tests/test_validation.py`
  - `tests/test_anomaly.py`
  - `tests/test_explanations.py`
- 更新:
  - `src/oscillo_plasma_calc/report/trace.py` (TraceResult 拡張)
  - `src/oscillo_plasma_calc/pipeline.py` (anomaly 自動付与)
  - `src/oscillo_plasma_calc/ui/app.py` (Upload 再設計、各タブガイド、Trace カード改修)

---

## 9. 検証計画（end-to-end）

### A. 機能検証
- 正常な PW_1p50.csv → すべて ✓ 表示、Trace カードに 3 レベル解説
- 列名崩れの broken.csv → 赤バナー、計算走らず、列名の修正ガイドが出る
- Vpp が 200 V（人為的に縮小）→ ⚠ 警告、「電源出力不足 / プローブ校正」原因候補、2013_CAP-13-1050 リンク
- Te = 100 K（ダミー OES で）→ ⚠ 警告、「LTE 未成立 / 線選択不良」

### B. UX 検証（研究者ヒアリング）
- 学部 4 年生（新配属）に見せて「Vpp が何の指標か」を 30 秒以内で答えられるか
- M2 に見せて「この値は典型範囲内か」が 10 秒以内で判定できるか
- PI に見せて「なぜこの警告が出たか」の判断材料が揃っているか

### C. pytest
- 23〜30 passed 想定（既存 21 + 新規 6〜9）

---

## 10. 根拠となる最新論文・文献

### UI/UX / Human Factors
- Nielsen, J. (1994) "10 Usability Heuristics for User Interface Design"
- Munzner, T. (2014) "Visualization Analysis and Design" CRC Press
- Sarikaya & Gleicher (2018) "Design Factors for Summary Visualization in Visual Analytics" IEEE TVCG 24(1)
- Sweller, J. (1988) "Cognitive Load During Problem Solving" Cognitive Science
- Midway, S. R. (2020) "Principles of Effective Data Visualization" Patterns 1(9)
- Few, S. (2013) "Information Dashboard Design" Analytics Press

### 科学データ可視化（最近）
- Satyanarayan et al. (2017) "Vega-Lite: A Grammar of Interactive Graphics" IEEE TVCG
- Feng et al. (2023) "An Evaluation of Dashboard Design Patterns for Scientific Data" (CHI 2023)
- Bettencourt et al. (2022) "Designing Data-Intensive Dashboards for Scientific Work"

### 計算ソフトの研究者向け設計
- Wilson et al. (2017) "Good enough practices in scientific computing" PLOS Comput Biol
- Perkel, J. (2021) "Reactive, reproducible, collaborative: computational notebooks evolve" Nature

### 野村研究室の判断材料（計算結果の典型範囲）
- 2006_JJAP-45-8864 (水中 RF プラズマ)
- 2009_JAP-106-113302 (空間分解 OES)
- 2009_POP-16-033503 (Stark 広がり)
- 2011_PSST-20-034016 (導電率依存)
- 2013_CAP-13-1050 (ns-pulse 破壊特性)
- 2017_JEPE-10-335 (化学効率)
- 2012_IJHE-37-16000 (G 値)

---

## 11. 2026-04-23 研究室定例ミーティング議事録との整合

本 UX 再設計は、2026-04-23 の定例（野村先生・中島先生・林・千葉・石井・菅・小山ほか）での議論と完全に整合する。議事録からの主要決定と、本ソフトでの実装対応を以下に記す。

### 11.1 議事録主要決定（抜粋）

1. **電力計測は高額電力量計を買わず、既存オシロ波形から Python で積分して求める**
2. 計算値は **値＋導出数式＋仮定＋単位** の完全セットで共有する
3. 野村先生指示: **LTE（局所熱平衡）を実測で確認する** — タングステン電極の 4 本線 Boltzmann plot の直線性 (R²) で判定
4. 触媒実験は **懸濁 → 固定 → 電極材化** の順で比較
5. 中島先生指示: **コンセント側の総消費電力と突き合わせて妥当性検証** — 待機電力を分離
6. 研究データは **LINE 共有後 1 週間以内にローカル DB へ保全** → 小山担当

### 11.2 本ソフトでの対応マトリクス

| 議事録の要件 | 本ソフトでの実装状況 | 対応ファイル |
|---|---|---|
| オシロ波形から電力を Python で積分 | ✓ 実装済み（P(t)・E・P̄・Lissajous） | `electrical/*.py` |
| 「値＋数式＋代入＋単位＋根拠論文」を完全セットで表示 | ✓ `TraceResult` と Trace タブの 3 レベル解説で実装 | `report/trace.py`, `ui/app.py` |
| タングステン 4 本線 Boltzmann plot の直線性評価 | ✓ `R²` を算出、LTE 成立度ラベル付与 | `spectroscopy/boltzmann_plot.py` |
| 前処理: DC オフセット補正 | ✓ Upload タブでチェックボックス有効化で自動適用 | `signal/preprocess.py` |
| 前処理: 時間軸同期（最初の立ち上がりエッジを t=0 に） | ✓ Upload タブで有効化可 | 同上 |
| コンセント側総消費電力との比較 | ✓ Upload サイドバーで W_socket 入力 → Electrical タブで `P̄ / W_socket` を自動表示 | `ui/app.py` |
| エタノール分解実験（GC-MS 後処理） | ☐ 未実装（Chemistry タブ入力を GC データ直結に拡張可能、次フェーズ） | `chemistry/` |
| 触媒反応の理論モジュール | ☐ 未実装（Arrhenius 式は `theory_reference.md` 第 8 章で将来拡張候補として提示） | — |
| データ DB / 長期保存（小山タスク） | ☐ 本アプリスコープ外。別プロジェクト（Quarto + Cloudflare Pages は `publish_and_render_plan.md` に設計済み） | `docs/publish_and_render_plan.md` |

### 11.3 会議発言との細部対応

- **中島先生「電圧のピークと電流のピークに ~0.3 μs 時差がある」** → Waveform タブの「このタブの読み方」で「V と I のピーク時間差 ⇔ 抵抗性／誘導性／容量性負荷の判別」として明示。
- **野村先生「LTE が成立するところに触媒反応させなきゃいけない」** → 励起温度 Te タブの guide に「R² ≥ 0.95 ⇔ LTE 成立確度高い」と記載、数値判定を UI で即時表示。
- **野村先生「スペクトル線 3〜4 本以上ないと直線性が分からない」** → 「励起温度 Te」タブのガイドで「n ≥ 3 本推奨」「2 本では誤差大」と明示、R² 指標も `lte_quality_label` で評価。
- **中島先生「Pythonで計算する際は数式・手順・仮定まで出させろ」** → `TraceResult` に `equation_latex`, `substitution_latex`, `steps`, `sources` を全て格納。Trace タブで「📐 理論式（展開）」を開くと全部見える構造。
- **野村先生「家庭用電力計だと装置全体の電力になる。プラズマ部分は別」** → W_socket 比較機能で「P̄ / W_socket」%表示、待機電力の切り分け判断材料として機能。

### 11.4 アクションアイテムの本ソフト負担分（小山担当）

| AI | 期限 | 本ソフトとの関係 |
|---|---|---|
| 電力計算スクリプト（前処理〜積分〜レポート）ドラフト | 2026-05-09 | ✓ 本ソフトがそのまま該当。`scripts/run_analysis.py` CLI + Shiny UI。 |
| 計算フロー仕様書 | 2026-05-05 | ✓ `docs/theory_reference.md` + `docs/ux_redesign_researcher_plan.md` で網羅。 |
| コンセント側比較評価（林氏と共同） | 2026-05-11 以降 | ✓ 本ソフトの W_socket 比較機能で即対応可能。林氏が測定値を CSV と共に渡せば、Upload タブ入力だけで比較が出る。 |
| データ DB 設計 | 継続 | ☐ 本ソフトのスコープ外。`publish_and_render_plan.md` で Quarto + Cloudflare Pages 方式を提案済み。 |

---

## 12. 想定成果物

実装完了時、研究者体験は以下になる:

1. **CSV をドラッグ＆ドロップ** → 形式チェックが即座に走り、問題があれば対処法が表示される
2. **計算結果が色と記号付きで表示** → 正常（緑）/ 注意（青）/ 警告（黄）/ 異常（赤）が一目
3. **Trace タブで式を開く**と、自分のレベル（初学者/研究者/博士）に応じた解説が読める
4. **異常値に対しては、原因候補と引用論文が自動で表示** → 次のアクションが決めやすい
5. **表や図には「読み方」** が常時見えるので、新配属 B4 でも迷わない

油合成の研究者が、**装置の前に立ったときの思考プロセス（波形を見る → 疑う → 確認 → 記録）**と UI が一致するように設計する、これが本再設計のコアバリュー。
