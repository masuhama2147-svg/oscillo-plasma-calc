# 数式レンダリング完全修復 & 限定公開プラン 設計書

**目的**: 油合成研究者が、ブラウザ上で **論文品質の数式** を追え、かつ **研究室外のレビュワー（共同研究先・査読前のゲスト）にだけ URL を渡す形で公開** できる状態を作る。

本書は「① 根本修復（最新 OSS）」と「② 限定公開の実装計画」を一枚にまとめたもの。

---

## 1. 現状の症状と根本原因

### 1.1 症状
スクショの通り、Trace タブで `$$ V_{pp} = V_{\max} - V_{\min} $$` が **LaTeX ソースのまま表示** されている。

### 1.2 原因（確定）

`ui/app.py` で各カード末尾に差し込んだ `_RETYPESET_JS` スクリプトは **一度も実行されていない**。理由は **HTML5 仕様**:

> "script elements inserted using innerHTML do not execute when they are inserted." — MDN

Shiny for Python の `@render.ui` は Server → Client に HTML を送り、**`htmltools` + `innerHTML`** で DOM を書き換える。結果、その HTML の中にある `<script>` タグは DOM 上には現れるが **実行されない**。

MathJax 自体はロードされているし、初回 `typesetPromise(document.body)` も走る。しかし **その時点で Trace の中身はまだ DOM に存在しない**（ユーザがタブを開いてサーバから reactive 送信を受けて初めて流入）。従って生 LaTeX のまま残る。

### 1.3 これまで試した対応が効かなかった理由のまとめ

| 対応 | なぜ効かなかったか |
|---|---|
| MathJax config を先頭に置く | 初回 typeset は走ったが、後から流入した DOM は対象外 |
| 各カード末尾に `<script>` を仕込む | **innerHTML 経由の script は実行されない** （仕様） |
| `async` 外して順序固定 | 初期化は健全化したが、動的挿入問題は独立 |

**正解は、ページ全体に MutationObserver を張って DOM 変化を能動的に捉え、そのたびに再レンダする方式**。MathJax でも実現できるが、下記の通り KaTeX の方が軽量かつ同期レンダで安定。

---

## 2. 採用する最新 OSS：KaTeX v0.16 + auto-render + MutationObserver

### 2.1 候補比較（2024〜2026 時点で実用的な OSS）

| ライブラリ | バンドルサイズ | レンダ方式 | 動的 DOM | オフライン化 | LaTeX 互換 | 選択理由 |
|---|---|---|---|---|---|---|
| **KaTeX 0.16.11** | ~290 KB (min+gzip ~80 KB) | **同期** DOM 直描画 | auto-render + MutationObserver で堅牢 | easy（npm or pip） | Khan Academy 品質、AMS / physics に近い対応 | **最有力** |
| MathJax 3 (tex-mml-chtml) | ~420 KB (min+gzip ~130 KB) | **非同期** Promise | typesetPromise を自分で呼ぶ必要 | 可能 | 最広。custom macro 可 | 互換性重視なら |
| Temml 0.10.x | ~200 KB | ブラウザ内で LaTeX→MathML | MathML にすれば以後ネイティブ | yes | ~95 % LaTeX | Firefox で最軽量 |
| Typst (2024 OSS) | - | サーバ側で SVG 事前生成 | 完全静的 | yes | Typst 構文で書き直し要 | LaTeX 非互換のため本件には不向き |

**選定**: **KaTeX 0.16.11**。理由:
- **同期レンダ** なのでチラつきが無い。Shiny の reactive 更新と相性最良。
- `auto-render` 拡張で `$$...$$` をそのまま拾える → 既存の LaTeX コードを 1 文字も書き換え不要。
- MutationObserver で `document.body` 全体を監視すれば **Shiny が DOM を書き換えた瞬間に即レンダ**。
- ライセンス MIT、CDN/npm/pip どれでも配布可能。

### 2.2 実装計画

#### A. `ui/app.py` の header を KaTeX に差し替え

```python
# 既存の MATHJAX_CONFIG, MATHJAX_CDN を削除し、以下に置換

KATEX_CSS = ui.tags.link(
    rel="stylesheet",
    href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css",
    integrity="sha384-nB0miv6/jRmo5UMMR1wu3Gz6NLsoTkbqJghGIsx//Rlm+ZU03BU6SQNC66uf4l5+",
    crossorigin="anonymous",
)
KATEX_JS = ui.tags.script(
    src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js",
    integrity="sha384-7zkQWkzuo3B5mTepMUcHkMB5jZaolc2xDwL6VFqjFALcbeS9Ggm/Yr2r3Dy4lfFg",
    crossorigin="anonymous",
    defer="defer",
)
KATEX_AUTO = ui.tags.script(
    src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js",
    integrity="sha384-43gviWU0YVjaDtb/GhzOouOXtZMP/7XUzwPTstBeZFe/+rF4+jyBgOg/rLqjHwl4",
    crossorigin="anonymous",
    defer="defer",
)
KATEX_BOOT = ui.tags.script(ui.HTML(r"""
(function(){
  const OPTS = {
    delimiters: [
      {left: '$$', right: '$$', display: true},
      {left: '\\[', right: '\\]', display: true},
      {left: '$',  right: '$',  display: false},
      {left: '\\(', right: '\\)', display: false},
    ],
    throwOnError: false,
    strict: 'ignore',
  };
  function renderAll(node){
    if(window.renderMathInElement) renderMathInElement(node, OPTS);
  }
  // 初回 DOM 完成時
  document.addEventListener('DOMContentLoaded', () => renderAll(document.body));
  window.addEventListener('load', () => renderAll(document.body));
  // Shiny が挿した新ノードを追尾
  const obs = new MutationObserver((muts) => {
    muts.forEach(m => {
      m.addedNodes.forEach(n => {
        if (n.nodeType === 1) renderAll(n);
      });
    });
  });
  obs.observe(document.body, {childList: true, subtree: true});
})();
"""))

app_ui = ui.page_navbar(
    ...,
    title="液中プラズマ オシロスコープ解析",
    header=ui.TagList(KATEX_CSS, KATEX_JS, KATEX_AUTO, KATEX_BOOT),
)
```

#### B. `trace_to_html` から `_RETYPESET_JS` を削除

KaTeX + MutationObserver にすれば per-card スクリプトは不要。依存が消える分、コードも単純になる。

#### C. 書き換えなしで済む既存資産

- `equation_latex`, `substitution_latex` の LaTeX ソース全て（KaTeX は `\frac`, `\left|`, `\right|`, `\dfrac`, `\times`, `\text{}`, `\mathrm{}`, `\,` 全対応）
- `format_si()`, `pretty_number()`（既に生成している表記はそのまま）
- 理論式ドキュメント `docs/theory_reference.md`（GitHub Pages で描画する際にも KaTeX / MathJax を同じく使える）

#### D. KaTeX で非対応となる可能性のあるマクロ（洗い出し結果）

本プロジェクトで使っている LaTeX は全て KaTeX 対応範囲内:

| 使用マクロ | KaTeX 対応 |
|---|---|
| `\frac`, `\dfrac`, `\tfrac` | ✓ |
| `\sqrt`, `\sum`, `\int`, `\oint` | ✓ |
| `\left.`, `\right\|`, `\left\|`, `\right.` | ✓ |
| `\max_k`, `\min_k`, 添字 | ✓ |
| `\mathrm{}`, `\text{}`, `\mathbf{}` | ✓ |
| `\varepsilon_0`, `\lambda_D`, `\nu_i` | ✓ |
| `\bar{P}`, `\tilde{x}` | ✓ |
| `\,`, `\;`, `\!`, `\quad` | ✓ |
| `\times`, `\cdot`, `\approx` | ✓ |

`\oint`（閉曲線積分）も KaTeX 0.16 で正式対応。移行リスクゼロ。

#### E. フォールバックと品質保証

MutationObserver 非対応ブラウザは Safari 7+ / Chrome 18+ / Firefox 14+ / Edge 12+ 以降すべて対応済（実質 2014 年以降のすべて）。問題は無い。

万一 CDN 障害があっても、`pip install katex` してローカル配信するオプションあり（後述 §3.5）。

### 2.3 実装後の見え方（期待値）

現状 (before):
```
$$ V_{pp} = V_{\max} - V_{\min} $$
$$ V_{pp} = 3.68\,\text{kV} - (-3.12\,\text{kV}) = 6.8\,\text{kV} $$
```

修復後 (after):
```
         Vpp = Vmax − Vmin                 （綺麗な数式として描画）
         Vpp = 3.68 kV − (−3.12 kV) = 6.8 kV
```

数式は KaTeX の Computer Modern 系フォントで、分数は縦組、大きな積分・総和記号、適切なスペーシングで **学会発表のスライドクラスの品質** になる。

---

## 3. 限定公開（"limited release"）のインフラ設計

**要件**: 研究室関係者＋共同研究先＋ゲスト数名にだけ URL を渡したい。**全世界公開はしたくない**。

### 3.1 要素分解

システムは以下の 3 つに分離できる:

1. **インタラクティブアプリ** — Shiny for Python（本体）
2. **ドキュメント**（理論式リファレンス・設計書群） — 静的 HTML
3. **データ**（xlsx、論文アーカイブ、将来の測定 CSV） — **絶対に公開しない**

各々の公開方針を独立に決めるのが実運用上正解。

### 3.2 Shiny アプリの限定公開プラットフォーム比較

| サービス | 無料プラン | 限定公開の実現 | 制限 / 懸念点 |
|---|---|---|---|
| **shinyapps.io**（Posit 公式） | 5 app / 25 時間/月 | 無料プランは **public only** | パスワード保護は Starter プラン $9/月〜 |
| **Posit Connect Cloud**（2024 リリース） | 無料枠あり | 招待制 + Google OAuth ログイン | Shiny for Python 正式対応、R Connect より新しい |
| **Hugging Face Spaces** | 公開: 無料、**private: Pro $9/月** | Docker or Gradio/Streamlit native（Shiny は Docker 経由） | 無料 private は無し（URL 難読化止まり） |
| **Railway** | $5 credit / 月 | カスタムドメイン + Basic Auth ミドルウェア | Docker デプロイ、スリープ無し |
| **Render** | 750 時間/月、スリープ有 | Basic Auth via nginx sidecar | 初回アクセスで 30 秒スリープ復帰 |
| **Fly.io** | 3 shared-cpu-1x VM 無料 | IP allowlist + OAuth proxy | Docker、リージョン選択可 |
| **自前 VPS** (Vultr/Hetzner/ConoHa) | ¥500〜/月 | Cloudflare Tunnel + Cloudflare Access (Zero Trust 無料枠) | 完全コントロール、IP/メール allowlist 可 |

#### 推奨: **Posit Connect Cloud** を第一候補、代替は **Fly.io + Cloudflare Access**

**理由**:
- Posit Connect Cloud は Shiny for Python の **公式** 新世代クラウド（2024 リリース）で、現在 **招待制の限定公開をサポート**。Google OAuth で研究室 Google アカウントのみにアクセス制限可能。Posit 公式の安定性が期待できる。
- Fly.io + Cloudflare Tunnel の組合せは、**完全に無料で、IP allowlist / メール allowlist / One-time PIN** で限定公開でき、運用経験を残せる。少し技術的だが、研究室として「再現可能な公開手順書」を残せる価値。

#### 非推奨
- **shinyapps.io** 無料プラン: パスワード無しで公開 URL 一本だけ → 研究室運用には脆弱
- **URL 難読化のみ（HuggingFace Spaces public）**: URL が漏れた瞬間に全世界公開になるリスク

### 3.3 ドキュメントの公開

`docs/theory_reference.md`, `docs/ui_redesign_explanation.md`, `docs/math_rendering_fix.md`, 本書を読める状態にする。

| 方式 | 静的 HTML の生成 | ホスティング | 限定公開 |
|---|---|---|---|
| **GitHub Pages + MkDocs Material** | `mkdocs build` | GitHub Pages (public) | Enterprise で private pages、or **GitHub Private + Codespaces 経由で閲覧** |
| **GitHub Pages + Quarto** | `quarto render` | 同上 | 同上 |
| Cloudflare Pages | git push → auto build | 無料、カスタムドメイン | Cloudflare Access でメール allowlist |
| Vercel / Netlify | 同上 | 無料 | Password protect 有料 |

**推奨**: **GitHub Private Repository + Quarto** で手元ビルドし、成果 HTML を **Cloudflare Pages の Private プロジェクト** にデプロイ。Cloudflare Access 無料枠でメール allowlist（最大 50 users/tenant 無料）。

Quarto を選ぶ理由:
- **数式ネイティブ対応**（KaTeX / MathJax 両対応、既存 `.md` が無変換で使える）
- R / Python / Julia のコードを **実行しながら** ドキュメントに組込める（将来「実データでこのセルを走らせた結果」を載せる時に必須）
- Posit 公式で Shiny と同じエコシステム
- MIT ライセンス

### 3.4 データ・成果物の取扱い

**必ず `.gitignore` に入れるもの**:
```
# 絶対公開しない
オシロスコープ測定結果.xlsx
野村研究室_論文アーカイブ.xlsx
励起温度計算シート ver.2.xlsx
data_csv/*.csv
data_csv/!_template.csv    # テンプレートだけは OK
reports/*.md               # 実データ由来のレポート
.venv/
__pycache__/
```

**公開してよいもの**:
- `src/oscillo_plasma_calc/**` (計算ロジックのソース)
- `tests/**`
- `scripts/**`
- `docs/**` (本書含む理論ドキュメント)
- `pyproject.toml`, `README.md`

**IP・著作権の配慮**:
- `野村研究室_論文アーカイブ.xlsx` は **社内管理資産** → 絶対に commit しない
- 論文引用 ID (`2013_CAP-13-1050` 等) のみが露出する状態が妥当
- 実測波形 (`オシロスコープ測定結果.xlsx`) は「研究途中データ」扱いで非公開
- 発表・投稿の準備ができた時点で、**公開用の合成波形サンプル** を別途 `examples/` に用意して公開

### 3.5 具体的な公開手順（推奨構成）

#### ステップ 1: GitHub Private Repo を作る

```bash
cd /Users/koyamatakuto/Downloads/野村研究室計算ソフト開発
git init
# .gitignore 整備（上記項目）
git add pyproject.toml README.md src/ tests/ scripts/ docs/
git commit -m "initial: oscilloscope plasma calculation tool"
gh repo create nomura-lab/oscillo-plasma-calc --private --push
```

#### ステップ 2: Quarto でドキュメントをビルド

```bash
# Quarto インストール: brew install quarto
mkdir -p site && cp docs/*.md site/
cat > site/_quarto.yml << 'EOF'
project:
  type: website
  output-dir: _output
website:
  title: "野村研究室 液中プラズマ計算ソフト"
  navbar:
    left:
      - href: theory_reference.qmd
        text: 理論式リファレンス
      - href: ui_redesign_explanation.qmd
        text: UI 解説設計
      - href: math_rendering_fix.qmd
        text: 数式レンダリング
      - href: publish_and_render_plan.qmd
        text: 公開プラン
format:
  html:
    toc: true
    html-math-method: katex
    theme: cosmo
EOF
# .md を .qmd にリネーム
for f in site/*.md; do mv "$f" "${f%.md}.qmd"; done
cd site && quarto render
```

#### ステップ 3: Cloudflare Pages + Access で限定公開

```bash
# site/_output を Cloudflare Pages にデプロイ
# （dashboard: Pages > Create project > Connect to GitHub）

# Cloudflare Access ルール:
#   Application: oscillo-plasma-calc.pages.dev
#   Policy: "Allow emails matching @nomura-lab.example.jp OR
#            specific emails: collaborator1@foo.com, ..."
#   Session duration: 24h
```

#### ステップ 4: アプリ本体を Posit Connect Cloud にデプロイ

```bash
# https://connect.posit.cloud/ でサインアップ
# GitHub リポジトリを連携
# deploy 設定で App entry point = src/oscillo_plasma_calc/ui/app.py
# Access control = "Invited users only" で研究室 Google アカウントを追加
```

#### ステップ 5: データはどこにも commit しない

実測波形は研究室 NAS / Google Drive 共有で管理、アプリには **ユーザがブラウザから CSV アップロード** して使う運用にする（既に実装済み）。

### 3.6 コスト見積り（月額、2026 時点想定）

| 項目 | 無料枠 | 想定利用 | 実費 |
|---|---|---|---|
| GitHub Private Repo | 無料 (個人/学術) | OK | ¥0 |
| Cloudflare Pages | 無料 / 500 builds/mo | docs 更新 10 回/月想定 | ¥0 |
| Cloudflare Access (Zero Trust) | 50 ユーザ/mo 無料 | 研究室 10 + 共同研究 5 = 15 ユーザ | ¥0 |
| Posit Connect Cloud 無料プラン | 公開アプリ数・時間に制限あり（2026 時点要確認） | Shiny 1 app | ¥0 or Starter $9/mo |
| ドメイン（任意） | - | 任意、既存研究室ドメイン利用可 | ¥0〜¥1500/年 |
| 合計 | — | — | **¥0/月**（Posit 無料枠内に収まる場合） |

---

## 4. 実装スケジュール

### Step A (即時、本日完了可能): 数式レンダリング修復
1. `ui/app.py` header を MathJax → KaTeX に置換
2. `_RETYPESET_JS` を削除、`trace_to_html` を単純化
3. Shiny 再起動 → ブラウザで Trace タブ目視
4. pytest 21 passed 維持を確認

### Step B (1〜2 日): ドキュメント公開基盤
5. `.gitignore` 整備、秘匿データの除外確認
6. Quarto プロジェクト化（`_quarto.yml` 追加）
7. GitHub Private Repo 作成 & 初回 push
8. Cloudflare Pages 接続、初回ビルド確認
9. Cloudflare Access 設定、研究室メンバーを allowlist

### Step C (3〜5 日): アプリ本体の限定公開
10. Posit Connect Cloud アカウント作成（研究室 Google）
11. 環境変数 / secrets 設定（現状無し、将来の DB 接続に備える）
12. deploy テスト
13. 招待リスト作成、実アクセステスト

### Step D（継続）
14. 共同研究先に URL を配布、反応取り込み
15. 測定 CSV の受け渡しワークフロー整備（NAS / Drive）
16. 問題発生時の hotfix 手順書を README に追加

---

## 5. リスクと対策

| リスク | 対策 |
|---|---|
| Cloudflare Pages / Access の仕様変更で認証が壊れる | 当面は URL 難読化 + 内部共有メール経由のみで運用、1 ヶ月に 1 回アクセス確認 |
| Posit Connect Cloud 無料枠が突然有料化 | 代替として Fly.io + Docker 化の手順を `docs/deploy_failover.md` に用意（Step B 後に書く） |
| 論文アーカイブ xlsx を誤って commit | `.gitignore` 徹底 + `git-secrets` / `pre-commit` フック導入 |
| Shiny サーバが落ちて研究室メンバーから連絡 | `docs/runbook.md` を用意し、再起動手順（`./scripts/launch_ui.sh` 含む）を明記 |
| KaTeX で一部特殊マクロが描画されない | 本プロジェクトの LaTeX は KaTeX 対応範囲内であることを §2.2 D で確認済 |

---

## 6. 推奨アクション（提案まとめ）

### 今すぐ実装（A）
- KaTeX 方式で数式レンダリングを根本修復

### 今週中に整備（B + C）
- GitHub Private + Quarto + Cloudflare Pages でドキュメント公開（メール allowlist）
- Posit Connect Cloud でアプリ公開（Google OAuth）

### 進め方
- Step A だけ即時実行してもらい、ブラウザで数式が綺麗に描画されるか確認 → OK なら B 以降へ進む
- B 以降は秘匿データの取扱い (IP / 著作権) が絡むので、研究室責任者（野村先生 or 研究室 PI）に一度相談推奨

---

## 7. 参考リンク（社内ブックマーク用）

### KaTeX
- 公式: https://katex.org/
- auto-render 拡張: https://katex.org/docs/autorender.html
- サポート関数一覧: https://katex.org/docs/supported.html

### Shiny for Python 公開
- shinyapps.io: https://shiny.posit.co/py/docs/deploy-cloud.html
- Posit Connect Cloud: https://connect.posit.cloud/

### Quarto
- 公式: https://quarto.org/
- 数式組版: https://quarto.org/docs/authoring/markdown-basics.html#equations

### Cloudflare Zero Trust（無料 50 users）
- https://developers.cloudflare.com/cloudflare-one/policies/access/
- Access for pages: https://developers.cloudflare.com/cloudflare-one/applications/configure-apps/

### Fly.io（代替アプリホスト）
- Docker deploy: https://fly.io/docs/apps/launch/
