# Notion 品質改善 DB - インポートガイド

**目的**: Nomura Plasma Thermo-Chemical Twin の **精度・品質・拡張性を向上させる施策** を Notion DB で継続管理する。

**Notion で何ができる DB か**:
1. 改善施策の **進捗トラッキング**（Status: To Do / In Progress / Done / Blocked）
2. **優先度** で並べ替え（P1 / P2 / P3）
3. **カテゴリフィルタ**（数値精度 / UI / データ / インフラ / 文書 / 検証）
4. **担当者・期限** の管理
5. **依存関係**（前提タスクの relation）

---

## Notion へのインポート手順

### Option A: CSV 直接インポート（最速）

1. Notion で新しいページを作る → 「+」→「データベース」→「テーブル」
2. 右上の **「...」→「Merge with CSV」** をクリック
3. 同梱の `docs/notion_quality_db.csv` を選択
4. 列マッピング:
   - `Title` → `タイトル` (タイトル列)
   - `Category` → `カテゴリ` (Select)
   - `Priority` → `優先度` (Select: P1/P2/P3)
   - `Status` → `状態` (Select: Backlog/In Progress/Done/Blocked)
   - `Owner` → `担当`
   - `Effort_days` → `工数(日)` (Number)
   - `Module` → `モジュール`
   - `Description` → `説明`
   - `Acceptance` → `完了条件`
   - `References` → `参考`

### Option B: 手動構築（プロパティを完全に制御したい場合）

下記「DB スキーマ定義」セクションをコピーして、Notion で各プロパティを手動作成。

---

## DB スキーマ定義

| プロパティ名 | Notion 型 | 選択肢 / 説明 |
|---|---|---|
| **タイトル** | Title | 施策の 1 行サマリ |
| **カテゴリ** | Select | 数値精度 / UI / データ / インフラ / 文書 / 検証 |
| **優先度** | Select | P1（必須） / P2（推奨） / P3（あれば良い） |
| **状態** | Select | Backlog / In Progress / Done / Blocked / Deferred |
| **担当** | Person or Text | 担当者 |
| **工数(日)** | Number | 推定工数 |
| **モジュール** | Multi-select | thermo / equilibrium / plasma / ui / docs / qa / signal / electrical / chemistry / spectroscopy |
| **説明** | Text | 詳細・なぜ必要か |
| **完了条件** | Text | 「何ができたら done か」 |
| **参考** | Text | 関連論文・GitHub Issue・他のタスク |
| **作成日** | Created time | 自動 |
| **更新日** | Last edited time | 自動 |

### Notion ビュー（推奨）

1. **🎯 P1 優先**: Filter `優先度 = P1` & `状態 ≠ Done`、Sort `工数(日)` 昇順
2. **🚀 In Progress**: Filter `状態 = In Progress`、Group by `担当`
3. **📊 カテゴリ別**: Board view、Group by `カテゴリ`
4. **📅 ロードマップ**: Timeline view、X = `工数(日)`

---

## 品質改善施策（54 件、Notion へインポートする初期内容）

### 🔢 数値精度（10 件）

| # | タイトル | 優先度 | 工数 | モジュール | 説明 |
|---|---|---|---|---|---|
| 1 | CEA 元素ポテンシャル法で TP 平衡を 5–10 倍高速化 | P1 | 10 | equilibrium | 現状の SLSQP は 100 species で 1–3 秒。CEA RP-1311 §6.4 の Newton-Raphson 実装で 0.2 秒以下に。 |
| 2 | Wilhoit 外挿の `b` パラメータを species 別 DB 化 | P2 | 3 | thermo | 現状はユーザ指定。原子数・振動モード数から自動推定する DB を整備 |
| 3 | Stark 係数 α(Te) の Te 依存テーブル化 | P2 | 2 | plasma | Gigosos & Cardeñoso 1996 JPB 29:4795 の数値表埋込で誤差 30%→5% |
| 4 | Lissajous 変位電流補正（Peeters 2015） | P2 | 3 | electrical | モニタ Cm 入力欄追加、容量結合系での精度向上 |
| 5 | rise_time の `first_pulse` モード精度向上 | P2 | 2 | signal | プロミネンスとピーク窓を species ごとに最適化 |
| 6 | NASA9 区間境界での 2 階導関数連続性検査 | P3 | 2 | thermo | Cp の不連続を自動検出 |
| 7 | 多重解の HP / UV 平衡対応（複数初期値で並列求解） | P2 | 5 | equilibrium | Brent の単峰性仮定を緩和 |
| 8 | 二項 EEDF の 6 項展開拡張（高 E/N 対応） | P3 | 8 | plasma.eedf | 現状 1000 Td 超で警告のみ。多項展開で精度回復 |
| 9 | 反応速度の Arrhenius / Lindemann 表現追加 | P2 | 4 | chemistry | k(T) の温度依存を A·T^n·exp(-Ea/RT) で評価 |
| 10 | TP 平衡の凝縮相挿入ヒステリシス | P2 | 2 | equilibrium | 振動防止、once-in-stays-in しきい値導入 |

### 🎨 UI / UX（12 件）

| # | タイトル | 優先度 | 工数 | モジュール | 説明 |
|---|---|---|---|---|---|
| 11 | Shiny modularize: 12 タブを左サイドナビに階層化 | P1 | 5 | ui | タブ過多解消、研究フロー型ナビへ |
| 12 | Cantera ReactionPathDiagram の実図表示 | P1 | 5 | ui | graphviz 経由で C/H/O 元素フラックス図 |
| 13 | Equilibrium 計算の `extended_task` 非同期化 | P1 | 2 | ui | 1–3 秒の固まり防止 |
| 14 | Reaction Path タブの YAML を tab 式 sub-display に分離 | P2 | 1 | ui | テキスト + 可視化の併存 |
| 15 | Plotly 全体に `paper`/`screen` モード切替 を一貫適用 | P2 | 2 | ui | 論文補助図の品質統一 |
| 16 | チュートリアルモード（初回起動時の対話ガイド） | P2 | 5 | ui | B4 学生向けオンボーディング |
| 17 | 多条件比較タブ（PW0.5 / 1.0 / 1.5 / 2.0 を並列） | P1 | 5 | ui | Pareto front 可視化 |
| 18 | KaTeX で複雑な physics マクロサポート | P3 | 1 | ui | `\dv`, `\norm` 等 |
| 19 | UI/Plot のダークモード | P3 | 2 | ui | 夜間作業の目疲労低減 |
| 20 | Mobile レイアウトの最低限対応（M2/M4 iPad） | P3 | 4 | ui | フィールドでの参照用 |
| 21 | カードクリックでクリップボードに「再現コマンド」コピー | P2 | 1 | ui | provenance の活用 |
| 22 | 論文 Figure 用 PNG エクスポート | P2 | 2 | ui | 学会発表対応 |

### 📊 データ（8 件）

| # | タイトル | 優先度 | 工数 | モジュール | 説明 |
|---|---|---|---|---|---|
| 23 | LXCat デフォルト断面積セット（CO2/H2/H2O/CH4）同梱 | P1 | 1 | plasma.eedf | EEDF 計算の即時実用化 |
| 24 | 触媒系活性化エネルギー文献値 DB | P1 | 5 | chemistry | Arrhenius rate の入力データ |
| 25 | NIST Atomic Spectra DB から励起温度線情報自動取込 | P2 | 3 | spectroscopy | 現状は手動の xlsx 由来 |
| 26 | Burcat thermo データの追加取込（NASA9 補完） | P2 | 1 | thermo | 1500+ species の追加候補 |
| 27 | 凝縮相 species の名前 alias レイヤ | P2 | 2 | thermo | C(s) vs C(gr) などの名前正規化 |
| 28 | 野村研実験データ 100 例（オシロ + OES + GC）の整理 | P1 | 10 | docs | benchmark / 検証用 |
| 29 | 栗田電源仕様データの取込 | P2 | 1 | qa | 1 kW 予算の根拠強化 |
| 30 | GC-MS テキスト出力 loader（Shimadzu / Agilent） | P2 | 5 | chemistry | 手入力削減 |

### 🏗 インフラ（8 件）

| # | タイトル | 優先度 | 工数 | モジュール | 説明 |
|---|---|---|---|---|---|
| 31 | GitHub Actions CI yml を有効化 | P1 | 0.1 | infra | `gh auth refresh -s workflow` 後に push |
| 32 | Mac/Win/Linux × Py3.12/3.13 のマトリクスCI | P1 | 1 | infra | 既に yml 作成済 |
| 33 | DuckDB / SQLite で実験データの恒久保存 | P2 | 5 | infra | 小山担当（議事録 2026-04-23）|
| 34 | Quarto で docs/ サイト化 + Cloudflare Pages | P2 | 3 | docs | 限定公開ドキュメント |
| 35 | Posit Connect Cloud に Shiny app 公開 | P2 | 2 | infra | 共同研究先への配布 |
| 36 | Docker compose 化（CPU / GPU 切替） | P3 | 5 | infra | 再現環境の堅牢化 |
| 37 | uv ロックファイルで依存固定 | P2 | 1 | infra | Windows 初心者の再現性 |
| 38 | リリース GitHub Action（GitHub Release + Zenodo DOI） | P3 | 3 | infra | 引用可能版 |

### 📝 文書（8 件）

| # | タイトル | 優先度 | 工数 | モジュール | 説明 |
|---|---|---|---|---|---|
| 39 | 各タブの動画チュートリアル | P2 | 5 | docs | 学生向け OJT 効率化 |
| 40 | 論文 Methods 節 自動生成 | P1 | 3 | docs | 論文補助 |
| 41 | API リファレンス自動生成（mkdocstrings） | P2 | 1 | docs | 開発者向け |
| 42 | NASA RP-1271 / RP-1311 抜粋の docs/theory 化 | P2 | 2 | docs | 理論的根拠の透明化 |
| 43 | チュートリアル Notebook（Jupyter）整備 | P2 | 3 | docs | 学習ハードル下げ |
| 44 | 引用 BibTeX 自動エクスポート | P3 | 1 | docs | 論文執筆効率 |
| 45 | 共同研究先への onboarding 案内 PDF | P3 | 2 | docs | 共有ドキュメント |
| 46 | 設計判断ログ（ADR）の追加管理 | P3 | 2 | docs | 将来の保守性 |

### ✅ 検証（8 件）

| # | タイトル | 優先度 | 工数 | モジュール | 説明 |
|---|---|---|---|---|---|
| 47 | CEA 公式 example 40+ ケースの fixture 化 | P1 | 5 | tests | 平衡精度の継続保証 |
| 48 | BOLSIG+ vs Python 二項解の系統比較 | P1 | 3 | tests | EEDF 精度の定量化 |
| 49 | Cantera との TP 平衡 dual 検証 UI | P2 | 2 | ui | 研究者の信頼形成 |
| 50 | パフォーマンステスト（100/500/1000 species） | P2 | 2 | tests | スケーリング把握 |
| 51 | Property-based testing (Hypothesis) で SLSQP 健全性 | P3 | 3 | tests | エッジケース発見 |
| 52 | NASA polynomial vs JANAF の網羅検証 | P2 | 3 | tests | 50 species で Cp 1 % 一致確認 |
| 53 | UI Snapshot test (Playwright) | P3 | 5 | tests | UI レグレッション防止 |
| 54 | 数値検証スクリプトを CI に組込 | P1 | 1 | infra | 検証レポートの恒久化 |

---

## 重要度合計と工数配分

| カテゴリ | 件数 | 合計工数 | P1 件数 |
|---|---:|---:|---:|
| 数値精度 | 10 | 41 日 | 1 |
| UI/UX | 12 | 35 日 | 4 |
| データ | 8 | 28 日 | 2 |
| インフラ | 8 | 20.1 日 | 2 |
| 文書 | 8 | 19 日 | 1 |
| 検証 | 8 | 24 日 | 3 |
| **合計** | **54** | **167.1 日** | **13** |

P1（必須）13 件を全部こなすと **約 50 日 = 2 ヶ月**。研究室の他業務と並行して 4 〜 6 ヶ月で達成可能と見積もる。

---

## Notion での運用イメージ

```
┌────────────────────────────────────────────────────────────────┐
│ 📊 Nomura Plasma Twin - 品質改善 DB                            │
├────────────────────────────────────────────────────────────────┤
│ 🎯 P1 優先 (13)  ｜ 🚀 In Progress (3) ｜ 📊 By Category    │
├────────────────────────────────────────────────────────────────┤
│ ✓ #1  CEA 元素ポテンシャル法                  P1  10d  数値  │
│ ◯ #11 Shiny modularize 左サイドナビ          P1  5d   UI   │
│ ◯ #12 ReactionPathDiagram 実図表示           P1  5d   UI   │
│ ◯ #17 多条件比較タブ                          P1  5d   UI   │
│ ◯ #23 LXCat 断面積セット同梱                  P1  1d   data │
│ ◯ #24 触媒活性化エネルギー DB                 P1  5d   data │
│ ◯ #28 野村研実験データ 100 例 整理             P1  10d  data │
│ ◯ #31 GitHub Actions CI 有効化                P1  0.1d infra│
│ ◯ #32 OS×Py matrix CI                         P1  1d   infra│
│ ◯ #40 論文 Methods 自動生成                   P1  3d   docs │
│ ◯ #47 CEA fixture 40+                          P1  5d   tests│
│ ◯ #48 BOLSIG+ vs Python 二項比較               P1  3d   tests│
│ ◯ #54 数値検証 CI 組込                         P1  1d   infra│
└────────────────────────────────────────────────────────────────┘
```

---

## 同梱 CSV ファイル

`docs/notion_quality_db.csv` を Notion に直接インポート可能。
列: `Title, Category, Priority, Status, Effort_days, Module, Description, Acceptance, References`

54 行（上記の 54 件）を含む。
