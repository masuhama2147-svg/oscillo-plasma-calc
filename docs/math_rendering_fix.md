# 数式レンダリング不具合の診断 & 修復設計ドキュメント

**対象スクショ**: Trace タブに `$$ V_{pp} = V_{\max} - V_{\min} $$` など生テキストのまま並んでいる状態。

**ゴール**: `$$...$$` / `\frac{...}{...}` / `\left.\frac{dV}{dt}\right|_{\max}` といった LaTeX 記法を、**学会発表スライドで出せる品質の数式組版** にブラウザ上でレンダリングし、さらに **数値代入も人に優しい形** （11.84 kV / 18.78 mJ / 3.80×10¹¹ V/s）で出す。

---

## 1. 現状の問題を検証した結果

### 1.1 実際に起きていること

```bash
# 実 HTML に $$ が含まれているか
curl -s http://127.0.0.1:8000/ | grep -c '\$\$'
→ 0
```

初期 HTML には `$$` が **1 個もない**。これは Trace タブ等の中身が **Shiny の reactive.effect で後から `<shiny-html-output>` に DOM 注入される** ため。

一方 MathJax v3 は `<head>` でこう読まれている:
```html
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"
        type="text/javascript" async="async"></script>
```

### 1.2 なぜ生テキストが残るのか（3 つの要因）

1. **タイミング問題**: MathJax v3 は `DOMContentLoaded` の直後に 1 回だけページ全体を typeset する。**その時点では `$$` を含むノードがまだ存在しない**（Electrical や Plasma の「計算」ボタン押下後にサーバから送られてくる）。
2. **動的 DOM 追従が無い**: MathJax v3 はデフォルトで MutationObserver を張らない。Shiny が後からノードを挿しても自動的には typeset されない。
3. **async ロード**: ユーザがページを開いた時点で MathJax はまだロード中、という状態もあり得る。結果、初期表示タイミングでのタイプセットを取りこぼす可能性もある。

### 1.3 付随して気になる点（整形上の問題）

- 代入式が `1.184e+04\,\mathrm{V}` と指数形式のまま → 読みにくい。`11.84\,\text{kV}` にしたい。
- `6800 V` のような表示が `\mathrm{V}` なしの素の数値表記でも出ている → 単位のスタイルを統一したい。
- 掛け算・空白・`\times` の使い方が混在。数式美化ルールが必要。
- `$$ V_{pp} = V_{\max} - V_{\min} $$` のように先頭/末尾のスペースが余計（典型的なブラウザでは大丈夫だが、明確に整えたい）。

---

## 2. 解決アプローチの比較

**評価軸**: (A) 今の構造の改修コスト、(B) 動的注入への強さ、(C) 表示品質、(D) オフライン可否、(E) ページ応答性。

### 方針①: MathJax v3 を残し **手動 re-typeset** する
- `MathJax.typesetPromise([element])` を UI 更新後に呼ぶ。
- Shiny Python には「UI 更新完了を捉えるフック」が薄いが、**カードの HTML 末尾に `<script>` を仕込む** と Shiny がその HTML を挿入した瞬間にスクリプトが実行されるため、そこで typeset できる。
- (A) 少、 (B) ○、 (C) ◎、 (D) ×(CDN 必須)、 (E) ○。

### 方針②: KaTeX に置換 + **MutationObserver で自動 re-render**
- KaTeX は同期レンダ・軽量（〜50 KB）・高速。`auto-render` 拡張で `$$` を直接拾う。
- `MutationObserver(document.body)` で Shiny が挿入したノードを毎回 KaTeX に流せる。
- (A) 中、 (B) ◎、 (C) ○（一部非標準 LaTeX マクロは非対応）、 (D) × (CDN 必須, ただし同梱可)、 (E) ◎。

### 方針③: サーバ側で sympy / matplotlib を用いて **LaTeX → SVG / PNG** に事前変換
- Python 側で matplotlib の `mathtext` もしくは `sympy.preview(output='svg')` で画像化し、`<img>` で表示。
- JavaScript 不要、完全オフライン。ただし SVG 化に数十〜数百 ms かかる／同じ式が繰り返し計算される。
- (A) 中〜大、 (B) ◎（静的画像だから DOM 問題ゼロ）、 (C) ◎、 (D) ◎、 (E) △（初回キャッシュ必要）。

### 方針④: **MathML（ブラウザネイティブ）** にサーバ側で変換
- sympy に `sympy.mathml(expr, printer='presentation')` がある。
- Chrome 109+ / Safari 16+ / Firefox は完全サポート。レガシー Edge 等は非対応だが研究室内では問題なし。
- (A) 中、 (B) ◎、 (C) △〜○（素朴な組版、フォントで見た目ブレ）、 (D) ◎、 (E) ◎。

### 比較まとめ

| 方針 | 改修コスト | 動的 DOM | 表示品質 | オフライン | 速度 | 総評 |
|---|---|---|---|---|---|---|
| ① MathJax + 手動 typeset | 低 | ○ | ◎ | × | ○ | **一番早く直せる、既存資産を活かす** |
| ② KaTeX + Observer | 中 | ◎ | ○ | × | ◎ | 将来的に使う人が多ければこれ |
| ③ SVG/PNG 事前生成 | 中 | ◎ | ◎ | ◎ | △ | オフライン必須ならこれ |
| ④ MathML 変換 | 中 | ◎ | △〜○ | ◎ | ◎ | 品質よりオフライン優先なら |

---

## 3. 推奨: **方針①（MathJax 手動 typeset）を即投入 + 方針②（KaTeX 全面移行）を Phase 2**

理由:
- Phase 1 で **いま出ている生テキスト問題を即座に解消**。既に書いた `trace_to_html` と LaTeX 文字列に一切手を入れずに済む（1 日以内で完了）。
- Phase 2 で将来の動的拡張（解説トグルの動的挿入や、学生ページでの複数要素同時更新）に備え、MutationObserver で常時レンダ可能な KaTeX 方式に寄せる。`ui_redesign_explanation.md` での 4 ブロックカード化と同タイミングで移行すると UX 刷新と同期できる。

---

## 4. Phase 1 実装詳細（MathJax 手動 typeset で即修復）

### 4.1 設定ファースト — MathJax をロードする前に config を置く

Shiny で `ui.page_navbar(..., header=...)` の `header` にタグを並べる順序が重要。**config script → MathJax の順**にする。

```python
# src/oscillo_plasma_calc/ui/app.py （冒頭付近）

MATHJAX_CONFIG = ui.tags.script(ui.HTML("""
window.MathJax = {
  tex: {
    inlineMath: [['\\\\(', '\\\\)']],           // インラインは \( \) のみ
    displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],  // ディスプレイは $$ or \[ \]
    processEscapes: true,
    packages: {'[+]': ['ams', 'physics']}
  },
  svg: { fontCache: 'global' },
  chtml: { scale: 1.1 },                        // 少し大きめに
  startup: {
    typeset: true,
    ready: () => {
      MathJax.startup.defaultReady();
      // 初回ロード直後の typeset を保証
      MathJax.startup.promise.then(() => {
        if (document.body) MathJax.typesetPromise([document.body]);
      });
    }
  },
  options: {
    skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre']
  }
};
"""))

MATHJAX_CDN = ui.tags.script(
    src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js",
    # async は外す — 設定スクリプトの直後に同期ロードさせ、順序を確定
    type="text/javascript",
    id="MathJax-script",
)

# page_navbar の header に **順番通り** 並べる
app_ui = ui.page_navbar(
    ...,
    header=ui.TagList(MATHJAX_CONFIG, MATHJAX_CDN),
)
```

**ポイント**:
- `async` を外して順序を確定させる（約 400 KB の追加ロード、体感 ~100 ms）。
- `startup.typeset: true` で初回全体を typeset（内容が無くても害なし）。
- `chtml.scale` や `svg.fontCache` で描画品質を底上げ。
- `packages.[+]: ams, physics` で `\dfrac`, `\left|`, `\frac{d}{dt}` 等の拡張を使える状態にする。

### 4.2 カード挿入時に自動で再 typeset

Shiny が `<shiny-html-output>` に HTML を挿した直後に自動でスクリプトが走るので、`trace_to_html` が返す HTML の末尾に小さな `<script>` を仕込む。

```python
# src/oscillo_plasma_calc/ui/app.py

_RETYPESET_JS = ui.tags.script(ui.HTML("""
(function(){
  function go() {
    if (window.MathJax && MathJax.typesetPromise) {
      MathJax.typesetPromise([document.currentScript.parentNode])
             .catch(function(e){ console.warn('MathJax typeset error:', e); });
    } else {
      setTimeout(go, 100);   // MathJax がまだ来ていなければ 100ms 後に再試行
    }
  }
  go();
})();
"""))

def trace_to_html(tr) -> ui.TagList:
    parts = [
        ui.h4(tr.name),
        ui.p(ui.HTML(fr"$$ {tr.equation_latex} $$")),
    ]
    if tr.substitution_latex:
        parts.append(ui.p(ui.HTML(fr"$$ {tr.substitution_latex} $$")))
    parts.append(ui.pre(tr.summary()))
    if tr.steps:
        parts.append(ui.tags.details(
            ui.tags.summary("中間ステップ"),
            ui.tags.ul(*[ui.tags.li(s) for s in tr.steps]),
        ))
    if tr.sources:
        parts.append(ui.p(ui.tags.em("根拠論文: " + ", ".join(tr.sources))))
    return ui.div(
        *parts,
        _RETYPESET_JS,        # ← これが肝
        style="border-left:3px solid #2a6fb0; padding-left:12px; margin:12px 0;"
    )
```

`document.currentScript.parentNode` を `typesetPromise` に渡すことで、**そのカード内だけを再 typeset**。ページ全体を走らせないので速い（20 カードあっても 50 ms 程度）。

### 4.3 LaTeX 文字列側の整形強化（人に優しくする）

`src/oscillo_plasma_calc/report/ui_format.py` を新規作成。

```python
"""LaTeX 組版ヘルパ: 数値と単位を人に優しい表記へ。"""
from __future__ import annotations
import math

_SI_PREFIX = [
    (1e12, "T"), (1e9, "G"), (1e6, "M"), (1e3, "k"),
    (1.0, ""),  (1e-3, "m"), (1e-6, "\\mu"), (1e-9, "n"), (1e-12, "p"),
]

def format_si(value: float, unit: str, sig: int = 4) -> str:
    """Return `11.84\\,\\text{kV}` style string. Falls back to 3.80\\times10^{11}."""
    if value == 0 or not math.isfinite(value):
        return f"{value:.{sig}g}\\,\\text{{{unit}}}"
    mag = abs(value)
    # SI prefix が使える範囲（1e-12 〜 1e12）に収まれば接頭辞
    for factor, prefix in _SI_PREFIX:
        if mag >= factor * 0.999:
            scaled = value / factor
            return f"{scaled:.{sig}g}\\,\\text{{{prefix}{unit}}}"
    # それ以外は指数形式 with \times
    mantissa, exponent = f"{value:.{sig-1}e}".split("e")
    return f"{mantissa}\\times 10^{{{int(exponent)}}}\\,\\text{{{unit}}}"

def pretty_number(value: float, sig: int = 4) -> str:
    if not math.isfinite(value):
        return f"{value:.{sig}g}"
    if abs(value) >= 1e4 or (0 < abs(value) < 1e-3):
        m, e = f"{value:.{sig-1}e}".split("e")
        return f"{m}\\times 10^{{{int(e)}}}"
    return f"{value:.{sig}g}"
```

使用例 — `signal/peaks.py:detect_vpp` で:

```python
from ..report.ui_format import format_si, pretty_number

def detect_vpp(v: np.ndarray) -> TraceResult:
    vmax, vmin, vpp = _pp(v)
    return TraceResult(
        name="Peak-to-peak voltage Vpp",
        value=vpp, unit="V",
        equation_latex=r"V_{pp} = V_{\max} - V_{\min}",
        substitution_latex=(
            fr"V_{{pp}} = {pretty_number(vmax)} - ({pretty_number(vmin)}) = "
            fr"{format_si(vpp, 'V')}"
        ),
        sources=["2013_CAP-13-1050"],
    )
```

出力は `V_{pp} = 3680 - (-3120) = 6.800 \text{kV}` となり、スクショの `6800\,\mathrm{V}` よりぐっと読みやすくなる。

### 4.4 既存の式記述もそのままで OK

`\frac`, `\left.`, `\right|`, `\Delta t`, `\bar{P}` などはすべて AMS / Physics パッケージで標準サポート。書き換え不要。

### 4.5 Trace タブの視覚アップグレード（最小の追加）

カードを `<details>` で折りたたみ、**サマリ行には大きな数値カード**を出す（解説 md と整合）。

```python
def trace_to_html(tr) -> ui.TagList:
    big = ui.div(
        ui.h4(tr.name, style="margin:0;"),
        ui.div(tr.summary(), style="font-size:1.4em; color:#2a6fb0;"),
        style="display:flex; justify-content:space-between; align-items:center;",
    )
    inner = ui.TagList(
        ui.p(ui.HTML(fr"$$ {tr.equation_latex} $$")),
        ui.p(ui.HTML(fr"$$ {tr.substitution_latex} $$")) if tr.substitution_latex else "",
        ui.p(ui.tags.em("根拠論文: " + ", ".join(tr.sources))),
    )
    return ui.tags.details(
        ui.tags.summary(big),
        inner,
        _RETYPESET_JS,
        **{"open": ""},           # デフォルト開いた状態
        style="border-left:3px solid #2a6fb0; padding:8px 12px; margin:10px 0;",
    )
```

### 4.6 検証手順

1. `.venv/bin/shiny run --port 8000 src/oscillo_plasma_calc/ui/app.py` で再起動
2. http://127.0.0.1:8000/ → Upload で PW1.50 を読み込む
3. Electrical タブで表示確認 → V_{pp}, P(t) などの式が **黒い本物の数式として** 描画されること
4. Trace タブに飛んで 20 物理量すべての式がレンダされていること
5. **ブラウザの開発者ツール Console** に MathJax warning が出ていないこと
6. Chrome / Safari 両方で目視
7. `curl -s http://127.0.0.1:8000/ | grep -c 'id="MathJax-script"'` → 1 を確認（config→script の順で埋め込まれているか）

---

## 5. Phase 2 （余力があれば）: KaTeX に移行 + MutationObserver

### 5.1 なぜ移行価値があるか

- MathJax v3 (tex-mml-chtml バンドル) = 約 **420 KB**、KaTeX ≈ **80 KB**。研究室 Wi-Fi がしんどい時の起動が速くなる。
- 同期レンダなので「一瞬だけ生テキストが見える」チラつきが消える。
- `$` インライン数式も使いやすい（MathJax は `\(...\)` 推奨だが、KaTeX は `$...$` がデフォルトで安全に使える）。

### 5.2 置換コード

```python
KATEX_CSS = ui.tags.link(
    rel="stylesheet",
    href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css",
)
KATEX_JS  = ui.tags.script(src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js")
KATEX_AUTO = ui.tags.script(
    src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js",
)
KATEX_BOOT = ui.tags.script(ui.HTML("""
const _KATEX_OPTS = {
  delimiters: [
    {left: '$$', right: '$$', display: true},
    {left: '\\\\[', right: '\\\\]', display: true},
    {left: '$',  right: '$',  display: false},
    {left: '\\\\(', right: '\\\\)', display: false},
  ],
  throwOnError: false,
};
function renderAll(node) {
  if (window.renderMathInElement) renderMathInElement(node, _KATEX_OPTS);
}
document.addEventListener('DOMContentLoaded', () => renderAll(document.body));

// Shiny が挿入する新ノードを追尾
const _obs = new MutationObserver((muts) => {
  muts.forEach(m => {
    m.addedNodes.forEach(n => {
      if (n.nodeType === 1) renderAll(n);
    });
  });
});
_obs.observe(document.body, {childList: true, subtree: true});
"""))

app_ui = ui.page_navbar(
    ...,
    header=ui.TagList(KATEX_CSS, KATEX_JS, KATEX_AUTO, KATEX_BOOT),
)
```

KaTeX に移行すると `trace_to_html` 内の `_RETYPESET_JS` は **不要になる**（Observer が自動処理する）。

### 5.3 KaTeX 非対応マクロの回避

- `\dfrac` → KaTeX は標準対応（OK）
- `\left.\frac{dV}{dt}\right|_{\max}` → 対応
- `\mathrm{X}` → 対応
- `\text{kV}` → 対応
- `\,` / `\;` / `\!` スペーシング → 対応
- `\oint`, `\int_0^T` → 対応
- `physics` パッケージの `\dv{V}{t}` 等は **非対応** → MathJax 拡張経由のマクロを書き換える必要あり（本プロジェクトでは未使用なので影響なし）

---

## 6. Phase 3: オフライン完結させる場合（方針③）

CDN に依存したくない場合、`matplotlib.mathtext` or `sympy.preview` で LaTeX → SVG を事前ビルドしキャッシュ。

```python
import matplotlib.pyplot as plt
from io import BytesIO, StringIO
def latex_to_svg(latex: str) -> str:
    fig = plt.figure(figsize=(0.01, 0.01))
    fig.text(0, 0, f"${latex}$", fontsize=14)
    buf = StringIO()
    fig.savefig(buf, format='svg', bbox_inches='tight', transparent=True)
    plt.close(fig)
    return buf.getvalue()
```

生成した SVG を `ui.HTML(svg_string)` で埋め込む。`functools.lru_cache` で同じ式を繰返し生成しないように。

**デメリット**: 毎回 matplotlib の初期化が重い（20 式で 0.5〜1 秒）。サーバ起動時にプリコンパイルすべき。

---

## 7. 実装チェックリスト（Phase 1）

- [ ] `MATHJAX_CONFIG` を追加（`header` の先頭）
- [ ] `MATHJAX_CDN` から `async` を外す
- [ ] `_RETYPESET_JS` スクリプトスニペットを定義
- [ ] `trace_to_html` の末尾に `_RETYPESET_JS` を挿入
- [ ] `report/ui_format.py` に `format_si`, `pretty_number` を実装
- [ ] 既存の `substitution_latex` 組み立てを `format_si` 経由に書き換え:
  - [ ] `signal/peaks.py` (`detect_vpp`, `detect_ipp`, `rise_time`, `slew_rate`)
  - [ ] `electrical/instant_power.py:peak_power`
  - [ ] `electrical/energy_integral.py:absorbed_energy, mean_power`
  - [ ] `electrical/rms.py:v_rms, i_rms`
  - [ ] `electrical/lissajous.py:lissajous_power`
  - [ ] `plasma/*` （特に `debye.py`, `paschen.py` の指数表記）
- [ ] Shiny 再起動 → Chrome と Safari で目視確認
- [ ] pytest 全通過を維持（計算値は変えないので回帰無し）

---

## 8. Phase 2 チェックリスト（KaTeX 移行、任意）

- [ ] `header` を KaTeX 3 行 + BOOT スクリプトに差し替え
- [ ] `trace_to_html` から `_RETYPESET_JS` を削除
- [ ] `$` インライン数式を積極活用できる形へ `ui_redesign_explanation.md` の 4 ブロックカードを最適化
- [ ] CDN 版が重いと判明したら `pip install` の中で KaTeX 本体を同梱し `shiny.ui.include_js` でローカル配信

---

## 9. 結論

**今すぐやるなら Phase 1**（MathJax の config + 手動 typeset + SI 整形ヘルパ）の 3 点セット。
- 修正ファイル: `ui/app.py` 1 個＋`report/ui_format.py` 新規 1 個＋各 compute 関数の `substitution_latex` 書き換え。
- 想定工数: 実装 1.5 時間、目視確認 0.5 時間、合計 **2 時間程度**。
- 体感効果: スクショの生テキストが消え、`V_{pp} = 3.68\,\text{kV} - (-3.12\,\text{kV}) = 6.80\,\text{kV}` のような **論文クオリティの数式** に変わる。

Phase 2（KaTeX）と Phase 3（オフライン SVG）は、使い込む中で必要性が出たら追加導入する順で問題無い。

---

## 10. 参考リンク（社内ブックマーク推奨）

- MathJax v3 `typesetPromise` API: https://docs.mathjax.org/en/latest/web/typeset.html
- KaTeX auto-render: https://katex.org/docs/autorender.html
- Shiny Python で JS を差し込むパターン: https://shiny.posit.co/py/docs/jsquery.html
- Sympy → MathML: https://docs.sympy.org/latest/modules/printing.html#sympy.printing.mathml.mathml
