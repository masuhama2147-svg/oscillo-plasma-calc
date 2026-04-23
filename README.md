# 液中プラズマ オシロスコープ波形 & 発光分光 解析ソフト

野村研究室（液中プラズマ CO₂ 還元 → 液体燃料合成）の実験データを自動解析する、Python + Shiny for Python 製の研究用計算ソフトです。

![status](https://img.shields.io/badge/tests-45%20passed-success)
![python](https://img.shields.io/badge/python-3.12%2B-blue)
![license](https://img.shields.io/badge/license-research%20internal-lightgrey)

---

## 📋 このソフトで何ができるか

1. **オシロスコープで取ったパルス電圧・電流波形（CSV / xlsx）を入れると、電気系物理量を自動計算**
   - Vpp, Ipp, ピーク電力, 吸収エネルギー E, 平均電力 P̄
   - パルスエネルギー E_pulse, デューティ比 D, 実効平均電力 P_eff (= Ppeak·D)
   - RMS 値, Lissajous (Manley 法), FFT スペクトル
   - Crest/Form factor, 瞬時インピーダンス Z(t), 電力密度 p_vol

2. **プラズマ診断（発光分光データから）**
   - Boltzmann 2 本線法による電子温度 Te
   - Boltzmann plot (n 本線、H/O/W/Al/Cu 対応) + **R² による LTE 直線性判定**
   - Stark 広がりによる電子密度 ne
   - Debye 長, プラズマ周波数, Ohmic 加熱, Paschen 破壊電圧
   - **換算電場 E/N, 非平衡度 Te/Tgas, 振動温度 Tv** （非熱プラズマ診断）

3. **油合成 KPI（CO₂ プラズマ化学）**
   - SEI（比エネルギー投入量 kJ/mol）
   - エネルギーコスト EC, CO₂ 変換率 χ, 単位エネルギー変換効率 η_SE
   - Fischer-Tropsch ASF 連鎖成長確率 α
   - G 値, 化学効率 η, 生成物選択性

4. **装置運用の安全チェック**
   - 装置全体 1 kW 予算との自動照合（会議で決めた運用ルール）
   - コンセント側消費電力との比較
   - 冷却必要量 Q_cool の推定

5. **全物理量に「エラーライン」**（典型範囲を逸脱すると原因候補と参照論文が自動表示）

6. **全物理量に「初学者 / 研究者 / 博士」の 3 段階解説**

---

## 🚀 初心者向けインストール手順

前提: Python 3.12 以上 + インターネット環境

### 🍎 macOS（M1/M2/M3/M4 含む）

1. **Python を入れる**（入っていなければ）
   ```bash
   # ターミナル (/Applications/Utilities/ターミナル.app) を開いて:
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   brew install python@3.13 git
   ```
2. **このリポジトリを取ってくる**
   ```bash
   cd ~/Documents
   git clone <このリポジトリの URL>  # 下の「GitHub から取得」参照
   cd oscillo-plasma-calc
   ```
3. **仮想環境を作って依存をインストール**（1 回だけ）
   ```bash
   python3 -m venv .venv
   .venv/bin/pip install --upgrade pip
   .venv/bin/pip install numpy scipy pandas openpyxl sympy plotly matplotlib \
                         jinja2 shiny shinywidgets pytest pyyaml
   ```
4. **Shiny UI を起動**
   ```bash
   ./scripts/launch_ui.sh
   # → http://127.0.0.1:8000 にブラウザでアクセス
   ```
   または直接:
   ```bash
   .venv/bin/shiny run --port 8000 src/oscillo_plasma_calc/ui/app.py
   ```

### 🪟 Windows 10 / 11

1. **Python を入れる**（入っていなければ）
   - https://www.python.org/downloads/ から Python 3.13 をダウンロード → インストール時に **「Add Python to PATH」をチェック**
   - Git for Windows: https://git-scm.com/download/win からインストール

2. **PowerShell を開く**（スタートメニュー → Windows PowerShell）

3. **このリポジトリを取ってくる**
   ```powershell
   cd $HOME\Documents
   git clone <このリポジトリの URL>
   cd oscillo-plasma-calc
   ```

4. **仮想環境を作って依存をインストール**（1 回だけ）
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python -m pip install --upgrade pip
   .\.venv\Scripts\pip install numpy scipy pandas openpyxl sympy plotly matplotlib `
                                 jinja2 shiny shinywidgets pytest pyyaml
   ```

5. **Shiny UI を起動**
   ```powershell
   .\.venv\Scripts\shiny run --port 8000 src\oscillo_plasma_calc\ui\app.py
   # → http://127.0.0.1:8000 にブラウザでアクセス
   ```

   ※ 毎回打つのが面倒なら、プロジェクト直下に `launch_ui.bat` を作ると便利:
   ```bat
   @echo off
   cd /d %~dp0
   .\.venv\Scripts\shiny run --port 8000 src\oscillo_plasma_calc\ui\app.py
   pause
   ```
   これを **ダブルクリック** で起動できます。

### 🐧 Linux (Ubuntu / Debian)
```bash
sudo apt install python3 python3-venv python3-pip git
git clone <このリポジトリの URL>
cd oscillo-plasma-calc
python3 -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install numpy scipy pandas openpyxl sympy plotly matplotlib \
                      jinja2 shiny shinywidgets pytest pyyaml
./scripts/launch_ui.sh
```

---

## 🎓 使い方（初心者向け）

Shiny UI を開くと左に 8 つのタブがあります。

### 1. **Upload** タブ — まずここから
- 入力タイプを選ぶ:
  - 「CSV アップロード（推奨）」: 自分のオシロ CSV をドラッグ&ドロップ
  - 「別の xlsx パス」: xlsx ファイルのパスを指定
- CSV の受け入れ形式は **STEP 1** パネルに常時表示されるので、違反するとすぐ赤エラーで止まります
- オプション:
  - DC オフセット補正（推奨 ON）
  - コンセント側消費電力入力（会議要件）
- **「読み込む & 計算」**ボタンを押す → 電気系物理量が全部自動計算されます

### 2. **Waveform** — V(t) / I(t) の波形を見る
### 3. **Electrical** — 電力・エネルギー系のサマリ + P(t) プロット + Lissajous
### 4. **FFT** — 周波数スペクトル
### 5. **Plasma** — 発光分光 2 本線法で Te / ne を推定
### 6. **Chemistry** — GC データから G 値・化学効率・SEI などを計算
### 7. **励起温度 Te** — n 本線 Boltzmann plot（H/O/W/Al/Cu 対応、R² 表示）
### 8. **Trace** — 全物理量のダッシュボード（下記で詳細）
### 9. **Export** — Markdown レポートとして保存

### 各物理量のカードの読み方（Trace タブ）
```
┌──────────────────────────────────────────────┐
│ ピーク間電圧 Vpp   ℹ 注意                11.84 kV │ ← クリックで展開
├──────────────────────────────────────────────┤
│ 🔰 初学者向け（クリックで開く）            │
│ 🔬 研究者向け（クリックで開く）            │
│ 🎓 博士向け（クリックで開く）              │
│ 📐 理論式・数値代入                        │
│ ⚠ エラーライン判定                         │
└──────────────────────────────────────────────┘
```

Trace タブ上部のフィルタで「⚠警告・異常のみ」を 1 クリック → 問題のあるカードだけ見えます。

---

## 📁 データの扱い（重要 — 研究室 IP）

このリポジトリには **実測データ・論文アーカイブ Excel は含まれていません**。以下のファイルは `.gitignore` で確実に除外されています:

- `オシロスコープ測定結果.xlsx`
- `野村研究室_論文アーカイブ.xlsx`
- `励起温度計算シート ver.2.xlsx`
- `data_csv/*.csv`
- `reports/*.md`

これらは研究室内の NAS / Google Drive 共有経由で別途受け取ってください。**絶対に GitHub に push しないでください**（研究室の知的財産）。

---

## 🧪 テスト

```bash
.venv/bin/pytest -q     # 45 passed
```

内訳:
- `test_electrical.py`: 瞬時電力・エネルギー積分・RMS の解析値一致
- `test_plasma.py`: Boltzmann 逆算 / Debye オーダー / Stark 単調性
- `test_io.py`: xlsx / CSV 往復
- `test_spectroscopy.py`: 励起温度シート (H/O/W/Al/Cu) と数値一致
- `test_advanced_electrical.py`: パルス検出, Duty, Crest/Form, power density
- `test_oil_synthesis.py`: SEI, EC, χ, η_SE, ASF 回帰
- `test_nonequilibrium.py`: E/N, T_vib, 非平衡度
- `test_operational.py`: 1 kW 予算ルール判定

---

## 🏗️ プロジェクト構成

```
src/oscillo_plasma_calc/
├── io_layer/         xlsx / CSV 読み書き (Waveform dataclass)
├── signal/           フィルタ・ピーク検出・FFT・前処理 (DC/同期)
├── electrical/       瞬時電力・エネルギー・RMS・Lissajous
│   └── advanced.py   パルスエネルギー・Duty・Crest/Form・power density
├── plasma/           Boltzmann・Stark・Debye・Paschen・Ohmic
│   └── nonequilibrium.py    E/N・mean electron energy・T_vib
├── chemistry/        G 値・化学効率・選択性
│   └── oil_synthesis.py     SEI・EC・χ_CO2・η_SE・ASF
├── spectroscopy/     n 本線 Boltzmann plot (H/O/W/Al/Cu) + R²
├── qa/               CSV バリデータ・エラーライン判定・1 kW 予算
├── docs/             物理量の 3 レベル解説 + 典型範囲 DB
├── symbolic/         全理論式を sympy で一元定義
├── report/           Markdown レポート + LaTeX 整形ヘルパ
└── ui/               Shiny for Python UI

tests/                pytest（45 passed）
scripts/              CLI スクリプト 3 本
docs/                 設計ドキュメント群（下記参照）
```

---

## 📚 設計ドキュメント

プロジェクトの意思決定と理論背景は `docs/` 配下に全てある:

- [`theory_reference.md`](docs/theory_reference.md) — 理論式リファレンス（20+ 式、全て導出・前提・引用論文付き）
- [`ui_redesign_explanation.md`](docs/ui_redesign_explanation.md) — 研究者向け UI 設計の根拠
- [`math_rendering_fix.md`](docs/math_rendering_fix.md) — KaTeX 数式レンダリングの仕組み
- [`publish_and_render_plan.md`](docs/publish_and_render_plan.md) — 限定公開インフラ設計
- [`ux_redesign_researcher_plan.md`](docs/ux_redesign_researcher_plan.md) — UX 再設計（研究室会議と整合）
- [`advanced_theory_and_trace_ux_plan.md`](docs/advanced_theory_and_trace_ux_plan.md) — 高次理論式追加の技術設計

---

## 🎛️ 使用技術

| レイヤ | 技術 |
|---|---|
| 言語 | Python 3.12+ |
| 数値計算 | numpy 2.x, scipy 1.13+ |
| データ | pandas, openpyxl |
| 記号計算 | sympy（理論式を LaTeX で一元管理） |
| 可視化 | plotly, matplotlib |
| GUI | Shiny for Python (shiny 1.6+) |
| 数式表示 | KaTeX 0.16 + MutationObserver |
| 品質 | pytest, ruff |

---

## 🧾 引用

本ソフトを研究で使った場合は、以下の野村研究室論文を主要な根拠としてください:

- Mukasa, S. et al. (2009) "Temperature distributions of RF plasma in water" JAP 106:113302
- Mukasa, S. et al. (2009) "Spectroscopic measurement of electron density..." POP 16:033503
- Nomura, T. et al. (2008) "Comparison of RF and MW plasma in pure water" APEX 1:046002
- Nomura, K. et al. (2011) "Effects of liquid conductivity..." PSST 20:034016
- Nomura, K. et al. (2013) "Electrical breakdown under nanosecond pulse" CAP 13:1050
- Mochtar, A. A. et al. (2017) "Hydrogen production by in-liquid plasma" JEPE 10:335

その他の根拠論文は `docs/theory_reference.md` と各モジュールの docstring にまとめてあります。

---

## 📜 ライセンス

研究室内限定。外部公開時は野村先生・中島先生に確認必須。
