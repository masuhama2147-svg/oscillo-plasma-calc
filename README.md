# 液中プラズマ オシロスコープ波形 & 発光分光 解析ソフト

野村研究室（液中プラズマ CO₂ 還元 → 液体燃料合成）の実験データを自動解析する、Python + Shiny for Python 製の研究用計算ソフトです。

![status](https://img.shields.io/badge/tests-passing-success)
![python](https://img.shields.io/badge/python-3.12%2B-blue)
![license](https://img.shields.io/badge/license-research%20internal-lightgrey)

---

## 📋 このソフトで何ができるか — 料理に例えると

| 料理工程 | 本ソフトで対応すること |
|---|---|
| 火加減（コンロの火） | プラズマに入れる電圧と電流（オシロで測る） |
| 鍋の中の温度 | プラズマ内の電子温度・密度（分光器で測る） |
| 出来た料理の量 | できた油・メタノールの量（GC で測る） |

これら 3 種類の数字を入れると、**研究者が次に何を判断すべきかが画面に出ます**。

具体的には:
- **電気系**: Vpp, Ipp, ピーク電力, 吸収エネルギー E, 平均電力 P̄, 実効電力 P_eff（装置 1 kW 制約に直結）, RMS, Lissajous, FFT, 瞬時インピーダンス
- **プラズマ診断**: Boltzmann 2 本線/n 本線（H/O/W/Al/Cu）+ R² LTE 直線性判定, Stark, Debye, Paschen, **換算電場 E/N**, **非平衡度 Te/Tgas**, **振動温度 Tv**
- **油合成 KPI**: SEI, EC, χ_CO2, η_SE, **Fischer-Tropsch ASF α**, G値, η, 選択性
- **装置運用**: **1 kW 予算自動チェック**, η_dev, 冷却必要量
- **研究判断ゲート (G1-G6)**: データ品質 → エネルギー → Te 信頼度 → 熱力学 → 平衡 → 論文使用可否
- すべての値に **「初学者 / 研究者 / 博士」3 段階解説** + **エラーライン**（典型範囲逸脱時の原因候補と参照論文）

---

## 🪟 Windows 5 ステップセットアップ（超初心者向け）

> 「**コマンドラインを使ったことが無い**」「**Python って何？**」レベルの方を想定。

### 必要時間
インターネット環境で **30 分以内**。

### 必要なディスク容量
約 **600 MB**（Python + 仮想環境 + 依存パッケージ込み）。

---

### STEP 1. Python をインストール

1. https://www.python.org/downloads/ を開く
2. 黄色いボタン「Download Python 3.13.x」をクリック
3. 保存した `.exe` ファイルをダブルクリック
4. ⚠ **必ず最初の画面で「☑ Add Python to PATH」にチェック**（一番下のチェックボックス）
5. 「Install Now」をクリック → 数分で完了
6. 確認: スタートメニュー → `cmd` と入力 → 出てきた **コマンドプロンプト** で次を入力:
   ```
   python --version
   ```
   `Python 3.13.x` のように出れば成功。

> 失敗したら → [トラブルシューティング Q1](docs/troubleshooting.md#q1-python-は-内部コマンドまたは外部コマンドとして認識されていません)

---

### STEP 2. Git をインストール（コードを GitHub から持ってくるため）

#### 簡単派: GitHub Desktop を使う

1. https://desktop.github.com/ を開く
2. 「Download for Windows」をクリック → インストール
3. 起動して GitHub アカウントでサインイン

#### コマンド派: Git for Windows を使う

1. https://git-scm.com/download/win を開く
2. ダウンロード後、インストーラを **すべて Next** で完了（デフォルト設定で OK）
3. 確認: `cmd` で `git --version`

---

### STEP 3. リポジトリを取ってくる

#### GitHub Desktop の場合

1. GitHub Desktop の上メニュー: File → Clone Repository
2. URL タブを選択
3. 入力欄に貼り付け: `https://github.com/masuhama2147-svg/oscillo-plasma-calc`
4. Local path: `C:\Users\<あなた>\Documents\` のような **半角英数のみ** のパスを選ぶ（重要: 日本語フォルダ名は避ける）
5. Clone をクリック

#### コマンドプロンプトの場合

```cmd
cd %USERPROFILE%\Documents
git clone https://github.com/masuhama2147-svg/oscillo-plasma-calc.git
cd oscillo-plasma-calc
```

---

### STEP 4. 仮想環境を作って依存パッケージをインストール

コマンドプロンプトでプロジェクトフォルダに移動した状態で、**1 回だけ** 以下を順に実行:

```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

> 仮想環境 (.venv) が有効化されると、プロンプトの先頭に `(.venv)` が付きます。

3 行目の `pip install` は 2-5 分かかります。完了するまで待ってください。

> エラーが出たら → [トラブルシューティング Q5/Q6](docs/troubleshooting.md#q5-python--m-venv-venv-でエラー)

---

### STEP 5. 起動

#### 簡単派: ダブルクリック起動

`scripts\launch_ui.bat` を **エクスプローラからダブルクリック**。

⚠ Windows Defender SmartScreen の警告が出たら:
1. 「詳細情報」をクリック（小さく表示されている）
2. 「実行」をクリック
3. 一度許可すれば次回以降は出ません

#### コマンド派

```cmd
.venv\Scripts\shiny run --port 8000 src\oscillo_plasma_calc\ui\app.py
```

ブラウザで **http://127.0.0.1:8000** を開く（自動で開かなければ手動で URL を入力）。

> ブラウザが反応しない → [トラブルシューティング Q10/Q11](docs/troubleshooting.md#q10-ブラウザが自動で開かない)

---

## 🍎 macOS（M1/M2/M3/M4）セットアップ

```bash
# Homebrew が無ければ:
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Python と Git
brew install python@3.13 git

# リポジトリ取得
cd ~/Documents
git clone https://github.com/masuhama2147-svg/oscillo-plasma-calc.git
cd oscillo-plasma-calc

# 仮想環境
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 起動
./scripts/launch_ui.sh
# → http://127.0.0.1:8000 をブラウザで
```

---

## 🐧 Linux (Ubuntu/Debian)

```bash
sudo apt install -y python3 python3-venv python3-pip git
git clone https://github.com/masuhama2147-svg/oscillo-plasma-calc.git
cd oscillo-plasma-calc
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./scripts/launch_ui.sh
```

---

## 🎓 起動後の使い方

ブラウザで http://127.0.0.1:8000 を開くと、上部に **9 つのタブ** が並んでいます。

### おすすめの使う順番

1. **Upload** — まずここでデータを読み込む
   - 「既存 xlsx (同梱デモ)」を選んで「読み込む & 計算」を試す
   - 自分のデータは「CSV アップロード（推奨）」でドラッグ&ドロップ
2. **Waveform** — V(t) と I(t) の波形を目視確認
3. **Electrical** — Vpp/Ipp/E/P̄/Lissajous の表とプロット
4. **FFT** — 周波数スペクトルで駆動源を確認
5. **Plasma / 励起温度 Te** — 発光分光から Te / ne を推定（**R²<0.85 は参考値扱い**）
6. **Chemistry** — GC データから G値・SEI・η・ASF α
7. **Trace** — **🆕 G1-G6 ゲート + 全物理量ダッシュボード**
   - 上部に研究判断ゲート（G1 Data → G6 Research Valid）が表示
   - フィルタで「⚠警告のみ」表示も可
8. **Export** — Markdown レポート / 解析済み量 CSV ダウンロード

### 各カードの読み方
カードをクリックで展開:
- 🔰 初学者向け（新配属 B4 が読んで分かる）
- 🔬 研究者向け（M1〜PD 向け）
- 🎓 博士向け（前提・誤差・引用論文）
- 📐 理論式と数値代入
- ⚠ エラーライン（典型範囲逸脱時の原因と参照論文）

---

## 🆘 困ったときは

すべてのよくあるエラーと対処を [docs/troubleshooting.md](docs/troubleshooting.md) にまとめてあります。

それでも解決しないときは GitHub Issues に投稿:
https://github.com/masuhama2147-svg/oscillo-plasma-calc/issues

---

## 📁 データの取扱い（重要 — 研究室 IP）

このリポジトリには **実測データ・論文アーカイブ Excel は含まれていません**。`.gitignore` で確実に除外されています:

- `オシロスコープ測定結果.xlsx`
- `野村研究室_論文アーカイブ.xlsx`
- `励起温度計算シート ver.2.xlsx`
- `data_csv/*.csv`
- `reports/*.md`

これらは研究室内の NAS / Google Drive 共有経由で別途受け取ってください。**絶対に GitHub に push しないでください**（研究室の知的財産）。

---

## 🧪 テスト実行

```bash
.venv/bin/pytest -q     # 70+ tests, 全 passed
```

CI: GitHub Actions で macOS / Windows / Linux × Python 3.12/3.13 を毎 push でチェック。

---

## 🏗️ プロジェクト構成

```
src/oscillo_plasma_calc/
├── io_layer/         xlsx / CSV 読み書き (Waveform dataclass)
├── signal/           フィルタ・ピーク検出・FFT・前処理 (DC / 同期 / first_pulse モード)
├── electrical/       瞬時電力・エネルギー・RMS・Lissajous (PRF/window 二択)
│   └── advanced.py   パルスエネルギー・Duty・Crest/Form・power density
├── plasma/           Boltzmann 2 本線・Stark・Debye・Paschen・Ohmic
│   └── nonequilibrium.py  E/N・mean electron energy・T_vib
├── chemistry/        G値・化学効率・選択性
│   └── oil_synthesis.py   SEI・EC・χ_CO2・η_SE・ASF α
├── spectroscopy/     n 本線 Boltzmann plot (H/O/W/Al/Cu) + R² + is_te_reliable
├── qa/               CSV バリデータ・エラーライン判定・1 kW 予算・🆕 G1-G6 ゲート
├── docs/             物理量の 3 レベル解説 + 典型範囲 DB
├── symbolic/         全理論式を sympy で一元定義
├── report/           Markdown レポート + LaTeX 整形ヘルパ
└── ui/
    ├── components/   safe_filename, gate_panel, KPI rendering
    └── app.py        Shiny for Python (9 タブ + KaTeX + ゲート連動)

tests/                pytest（70+ tests passed）
scripts/              CLI スクリプト 3 本 + 起動 .sh / .bat
docs/                 設計ドキュメント 10+ 本
.github/workflows/    GitHub Actions CI (Mac/Win/Linux)
```

---

## 📚 設計ドキュメント

プロジェクトの意思決定と理論背景は `docs/` 配下:

- [`theory_reference.md`](docs/theory_reference.md) — 理論式リファレンス（20+ 式）
- [`IMPLEMENTATION.md`](docs/IMPLEMENTATION.md) — 実装内容 完全リファレンス
- [`formula_selection_rationale.md`](docs/formula_selection_rationale.md) — なぜその理論式を選んだか
- [`2026-05-02_status_report.md`](docs/2026-05-02_status_report.md) — 状況レポート（多視点）
- [`2026-05-02_numerical_critique.md`](docs/2026-05-02_numerical_critique.md) — 数値検証レポート（NASA grade 認定）
- [`2026-05-02_full_status_and_errors.md`](docs/2026-05-02_full_status_and_errors.md) — 統合状況 + エラー一覧
- [`troubleshooting.md`](docs/troubleshooting.md) — FAQ
- [`ui_redesign_explanation.md`](docs/ui_redesign_explanation.md) / [`ux_redesign_researcher_plan.md`](docs/ux_redesign_researcher_plan.md) — UI/UX 設計
- [`math_rendering_fix.md`](docs/math_rendering_fix.md) — KaTeX 数式レンダリング
- [`publish_and_render_plan.md`](docs/publish_and_render_plan.md) — 限定公開インフラ
- [`advanced_theory_and_trace_ux_plan.md`](docs/advanced_theory_and_trace_ux_plan.md) — 高次理論式追加と Trace UX
- [`researcher_ui_ux_visualization_plan.md`](docs/researcher_ui_ux_visualization_plan.md) — 研究者向け可視化強化

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
| 品質 | pytest, GitHub Actions CI |

---

## 🧾 引用

本ソフトを研究で使った場合は、以下の野村研究室論文を主要な根拠としてください:

- Mukasa, S. et al. (2009) "Temperature distributions of RF plasma in water" JAP 106:113302
- Mukasa, S. et al. (2009) "Spectroscopic measurement of electron density..." POP 16:033503
- Nomura, T. et al. (2008) "Comparison of RF and MW plasma in pure water" APEX 1:046002
- Nomura, K. et al. (2011) "Effects of liquid conductivity..." PSST 20:034016
- Nomura, K. et al. (2013) "Electrical breakdown under nanosecond pulse" CAP 13:1050
- Mochtar, A. A. et al. (2017) "Hydrogen production by in-liquid plasma" JEPE 10:335

その他の根拠論文は [`docs/theory_reference.md`](docs/theory_reference.md) と各モジュールの docstring にまとめてあります。

---

## 📜 ライセンス

研究室内限定。外部公開時は野村先生・中島先生に確認必須。
