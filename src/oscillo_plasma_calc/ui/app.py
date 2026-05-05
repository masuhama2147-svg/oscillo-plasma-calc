"""Shiny for Python: interactive analyzer UI.

Run:
    .venv/bin/shiny run --reload src/oscillo_plasma_calc/ui/app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# allow `shiny run <this file>` without installing the package
HERE = Path(__file__).resolve()
SRC = HERE.parent.parent.parent
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import numpy as np
import plotly.graph_objects as go
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_widget

from oscillo_plasma_calc.io_layer import load_xlsx, load_csv
from oscillo_plasma_calc.pipeline import analyze_electrical, _bind
from oscillo_plasma_calc.signal.fft import power_spectrum
from oscillo_plasma_calc.plasma import (
    electron_temperature_boltzmann,
    electron_density_stark,
    debye_length, plasma_frequency,
    ohmic_heating_density, paschen_breakdown_voltage,
)
from oscillo_plasma_calc.chemistry import g_value, chemical_efficiency
from oscillo_plasma_calc.chemistry.oil_synthesis import (
    specific_energy_input,
    energy_cost,
    co2_conversion_rate,
    single_pass_energy_efficiency,
    asf_chain_probability,
)
from oscillo_plasma_calc.plasma.nonequilibrium import (
    reduced_electric_field,
    mean_electron_energy,
    non_equilibrium_ratio,
)
from oscillo_plasma_calc.spectroscopy import (
    excitation_temperature, load_intensity_csv, list_elements, get_lines,
)
from oscillo_plasma_calc.report.markdown import build_markdown
from oscillo_plasma_calc.docs import get_explanation
from oscillo_plasma_calc.qa import validate_csv, evaluate_gates
from oscillo_plasma_calc.ui.components.gate_panel import render_gate_panel
from oscillo_plasma_calc.thermo import (
    lookup as thermo_lookup, export_cantera_yaml, cp_R_extrapolated,
)
from oscillo_plasma_calc.equilibrium import (
    equilibrium_tp, evaluate_condensed_insertion,
)
from oscillo_plasma_calc.ui.components import (
    anomaly_markdown,
    apply_research_plot_layout,
    display_value,
    export_trace_csv,
    figure_guidance_markdown,
    important_traces,
    paper_candidate_traces,
    safe_filename,
    status_label,
    waveform_annotations,
)


REPO_ROOT = SRC.parent
DEFAULT_XLSX = REPO_ROOT / "オシロスコープ測定結果.xlsx"


#
# KaTeX + MutationObserver による数式レンダリング。
#
# 理由: Shiny の `@render.ui` 経由で後から挿入される HTML に含まれる
# `<script>` は HTML5 仕様 (innerHTML) により実行されない。MathJax の
# per-card typeset 方式が機能しなかった根本原因はこれ。
# → ページ全体に MutationObserver を張り、動的挿入された全ノードに
#    KaTeX auto-render を掛ける方式に切替。
#
KATEX_VERSION = "0.16.11"
KATEX_CDN_BASE = f"https://cdn.jsdelivr.net/npm/katex@{KATEX_VERSION}/dist"

KATEX_CSS = ui.tags.link(
    rel="stylesheet",
    href=f"{KATEX_CDN_BASE}/katex.min.css",
    crossorigin="anonymous",
)
KATEX_JS = ui.tags.script(
    src=f"{KATEX_CDN_BASE}/katex.min.js",
    crossorigin="anonymous",
    defer="defer",
)
KATEX_AUTO = ui.tags.script(
    src=f"{KATEX_CDN_BASE}/contrib/auto-render.min.js",
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
      {left: '\\(', right: '\\)', display: false}
    ],
    throwOnError: false,
    strict: 'ignore',
    trust: false
  };
  let pending = false;
  function renderAll(root){
    if (!window.renderMathInElement) return;
    try { renderMathInElement(root, OPTS); }
    catch(e){ console.warn('KaTeX render error:', e); }
  }
  function scheduleRender(root){
    if (pending) return;
    pending = true;
    requestAnimationFrame(() => {
      pending = false;
      renderAll(root);
    });
  }
  function bootstrap(){
    renderAll(document.body);
    // Shiny が差し込む新ノードを逐次 render
    const obs = new MutationObserver(muts => {
      for (const m of muts) {
        for (const n of m.addedNodes) {
          if (n.nodeType === 1) scheduleRender(n);
        }
      }
    });
    obs.observe(document.body, {childList: true, subtree: true});
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootstrap);
  } else {
    bootstrap();
  }
  // 読み込み完了後の再 render 保険
  window.addEventListener('load', () => renderAll(document.body));
})();
"""))

MATH_HEADER = ui.TagList(KATEX_CSS, KATEX_JS, KATEX_AUTO, KATEX_BOOT)


def _trace_value_html(tr) -> str:
    """Return a short, bold, coloured summary value for the card header."""
    s = tr.scalar()
    if s is not None:
        import math as _math
        if _math.isfinite(s):
            magn = abs(s)
            if 1e-3 <= magn < 1e4 or s == 0:
                num = f"{s:.4g}"
            else:
                m, e = f"{s:.3e}".split("e")
                num = f"{m}×10<sup>{int(e)}</sup>"
            return f"{num} {tr.unit}"
        return f"{s} {tr.unit}"
    return tr.summary()


_LEVEL_COLORS = {
    "ok":      ("#1a7f37", "✓"),
    "notice":  ("#3a7bd5", "ℹ"),
    "warning": ("#c98a00", "⚠"),
    "error":   ("#c33333", "✗"),
}


def _anomaly_badge(anomaly) -> ui.TagList | str:
    if anomaly is None:
        return ""
    color, icon = _LEVEL_COLORS.get(anomaly.level, ("#666", "•"))
    return ui.tags.span(
        f" {icon} ",
        style=(f"background:{color}; color:white; padding:2px 8px; "
               f"border-radius:10px; font-size:0.75em; margin-left:8px;"),
        title=anomaly.message,
    )


def _anomaly_panel(anomaly) -> ui.TagList | str:
    if anomaly is None:
        return ""
    color, icon = _LEVEL_COLORS.get(anomaly.level, ("#666", "•"))
    parts = [
        ui.div(
            f"{icon} {anomaly.message}",
            style=(f"color:{color}; font-weight:600; margin-bottom:4px;"),
        )
    ]
    if anomaly.causes:
        parts.append(ui.div("可能性のある原因:", style="font-weight:600;"))
        parts.append(ui.tags.ul(*[ui.tags.li(c) for c in anomaly.causes]))
    if anomaly.references:
        parts.append(ui.div(
            "参考: " + ", ".join(anomaly.references),
            style="color:#666; font-size:0.9em;",
        ))
    return ui.div(
        *parts,
        style=(f"background:#fff7e6; border-left:3px solid {color}; "
               f"padding:8px 12px; margin:8px 0; border-radius:4px;"),
    )


def _explanation_sections(tr, open_beginner: bool = True) -> list:
    """3-level explanation toggles. Beginner open by default, others closed."""
    out = []
    if not tr.explanation_key:
        return out
    exp = get_explanation(tr.explanation_key)
    if exp is None:
        return out
    specs = [
        ("🔰 初学者向け", exp.beginner, "#e8f5ea", open_beginner),
        ("🔬 研究者向け", exp.researcher, "#e8f0fa", False),
        ("🎓 博士向け（前提・誤差・引用）", exp.phd, "#f5e8f0", False),
    ]
    for title, body, bg, open_ in specs:
        if not body:
            continue
        attrs = {"open": ""} if open_ else {}
        out.append(ui.tags.details(
            ui.tags.summary(title, style="cursor:pointer; font-weight:600;"),
            ui.div(body, style=f"padding:8px 12px; background:{bg}; "
                               f"border-radius:4px; margin-top:4px; line-height:1.6;"),
            **attrs,
            style="margin:8px 0;",
        ))
    if exp.references:
        out.append(ui.div(
            "📖 引用: " + ", ".join(exp.references),
            style="color:#666; font-size:0.85em; padding-left:4px;",
        ))
    return out


def trace_to_html(tr, compact: bool = True) -> ui.TagList:
    """Render a TraceResult card.

    compact=True (default for Trace tab):
      - card closed by default, header shows only name + value + badge
      - click to expand → 3-level explanations + formula + anomaly

    compact=False (used by per-tab panels like Plasma, Chemistry):
      - card open by default, beginner explanation visible immediately
    """
    big_value = ui.tags.span(
        ui.HTML(_trace_value_html(tr)),
        style=("font-size:1.35em; color:#2a6fb0; font-weight:600; "
               "white-space:nowrap;"),
    )
    header_row = ui.div(
        ui.div(
            ui.tags.span(tr.name, style="font-weight:600;"),
            _anomaly_badge(tr.anomaly),
            style="display:flex; align-items:center; min-width:0; flex:1;",
        ),
        big_value,
        style=("display:flex; justify-content:space-between; align-items:center; "
               "gap:18px; padding:4px 0;"),
    )

    explanations = _explanation_sections(tr, open_beginner=not compact)
    anomaly_panel = _anomaly_panel(tr.anomaly)

    formula_block = ui.tags.details(
        ui.tags.summary("📐 理論式・数値代入",
                        style="cursor:pointer; font-weight:600;"),
        ui.p(ui.HTML(fr"$$ {tr.equation_latex} $$")),
        *([ui.p(ui.HTML(fr"$$ {tr.substitution_latex} $$"))] if tr.substitution_latex else []),
        *([ui.tags.details(
            ui.tags.summary("中間ステップ"),
            ui.tags.ul(*[ui.tags.li(s) for s in tr.steps]),
        )] if tr.steps else []),
        *([ui.p(ui.tags.em("根拠論文: " + ", ".join(tr.sources)),
                style="color:#666; font-size:0.9em;")] if tr.sources else []),
        style="margin:8px 0;",
    )

    inner = list(explanations) + [formula_block]
    if anomaly_panel != "":
        inner.append(anomaly_panel)

    border_color = "#2a6fb0"
    if tr.anomaly is not None:
        border_color = _LEVEL_COLORS.get(tr.anomaly.level, ("#2a6fb0",))[0]

    # category → data attribute for JS-side filtering
    data_attrs = {"data-category": getattr(tr, "category", "other")}
    if tr.anomaly is not None:
        data_attrs["data-level"] = tr.anomaly.level
    else:
        data_attrs["data-level"] = "ok"

    details_attrs = dict(data_attrs)
    if not compact:
        details_attrs["open"] = ""

    return ui.tags.details(
        ui.tags.summary(header_row),
        *inner,
        **details_attrs,
        **{"class": "trace-card"},
        style=(f"border-left:4px solid {border_color}; border-radius:4px; "
               f"padding:8px 14px; margin:6px 0; background:#fafbfc;"),
    )


# Category display configuration
_CATEGORY_META = {
    "electrical":  ("⚡ 電気系", "#2a6fb0"),
    "plasma":      ("🌡️ プラズマ診断", "#7a4fb0"),
    "chemistry":   ("🧪 油合成 KPI", "#1a7f37"),
    "operational": ("🔌 装置運用", "#c98a00"),
    "other":       ("その他", "#666"),
}


def _trace_stats_header(traces: list) -> ui.TagList:
    """Sticky dashboard with counts + budget status (at the top of Trace tab)."""
    total = len(traces)
    counts = {"ok": 0, "notice": 0, "warning": 0, "error": 0}
    budget_tr = None
    for tr in traces:
        lvl = tr.anomaly.level if tr.anomaly else "ok"
        counts[lvl] = counts.get(lvl, 0) + 1
        if "budget" in (tr.explanation_key or ""):
            budget_tr = tr

    def chip(label, count, color):
        return ui.tags.span(
            f"{label} {count}",
            style=(f"background:{color}; color:white; padding:3px 10px; "
                   f"border-radius:12px; margin:0 4px; font-size:0.9em; "
                   f"font-weight:600;"),
        )

    budget_banner = ""
    if budget_tr is not None and budget_tr.anomaly is not None:
        color, icon = _LEVEL_COLORS.get(budget_tr.anomaly.level, ("#666", "•"))
        budget_banner = ui.div(
            ui.HTML(
                f"<strong>🔌 装置予算チェック:</strong> "
                f"<span style='color:{color}'>{icon} "
                f"{budget_tr.anomaly.message}</span>"
            ),
            style=(f"background:#fff; border:2px solid {color}; "
                   f"border-radius:6px; padding:10px 14px; margin-top:10px;"),
        )

    return ui.div(
        ui.div(
            ui.tags.strong(f"📊 解析サマリ  計算済: {total}"),
            chip("✓正常", counts.get("ok", 0), "#1a7f37"),
            chip("ℹ注意", counts.get("notice", 0), "#3a7bd5"),
            chip("⚠警告", counts.get("warning", 0), "#c98a00"),
            chip("✗異常", counts.get("error", 0), "#c33"),
            style=("display:flex; align-items:center; flex-wrap:wrap; "
                   "gap:6px;"),
        ),
        budget_banner,
        ui.div(
            ui.p("ℹ 各カードをクリックで展開 / 再度クリックで収納",
                 style="color:#666; font-size:0.85em; margin:6px 0 0;"),
            style="",
        ),
        style=("position:sticky; top:0; z-index:10; "
               "background:#f1f5f9; border:1px solid #cfd8dc; "
               "border-radius:8px; padding:12px 16px; margin-bottom:14px;"),
    )


# Filter chips + expand-all controls (client-side JS)
_TRACE_FILTER_JS = ui.tags.script(ui.HTML(r"""
(function(){
  function applyFilter(level) {
    document.querySelectorAll('.trace-card').forEach(el => {
      const lvl = el.getAttribute('data-level') || 'ok';
      const show = (level === 'all')
                 || (level === 'alert' && (lvl === 'warning' || lvl === 'error'))
                 || (lvl === level);
      el.style.display = show ? '' : 'none';
    });
  }
  function expandAll(open) {
    document.querySelectorAll('.trace-card').forEach(el => {
      if (open) el.setAttribute('open', ''); else el.removeAttribute('open');
    });
  }
  window.__traceApplyFilter = applyFilter;
  window.__traceExpandAll = expandAll;
})();
"""))


def _trace_controls() -> ui.TagList:
    btn = ("padding:6px 12px; margin:0 4px; border:1px solid #ccc; "
           "border-radius:16px; background:white; cursor:pointer; "
           "font-size:0.9em;")
    return ui.div(
        ui.tags.strong("フィルタ:"),
        ui.tags.button("全部", onclick="__traceApplyFilter('all')", style=btn),
        ui.tags.button("⚠警告・異常のみ", onclick="__traceApplyFilter('alert')", style=btn),
        ui.tags.button("✗異常のみ", onclick="__traceApplyFilter('error')", style=btn),
        ui.tags.span(" | ", style="margin:0 8px; color:#999;"),
        ui.tags.strong("展開:"),
        ui.tags.button("全部開く", onclick="__traceExpandAll(true)", style=btn),
        ui.tags.button("全部閉じる", onclick="__traceExpandAll(false)", style=btn),
        style=("display:flex; align-items:center; flex-wrap:wrap; gap:4px; "
               "padding:10px 14px; background:white; border:1px solid #eee; "
               "border-radius:6px; margin-bottom:10px;"),
    )


def _status_color(level: str) -> str:
    return _LEVEL_COLORS.get(level, ("#666", ""))[0]


def _kpi_table(title: str, traces: list, empty: str = "計算後に表示されます。") -> ui.TagList:
    rows = []
    for tr in traces:
        if tr is None:
            continue
        if tr.scalar() is None:
            continue
        level = status_label(tr)
        rows.append(ui.tags.tr(
            ui.tags.td(tr.name),
            ui.tags.td(display_value(tr), style="font-weight:700; text-align:right;"),
            ui.tags.td(tr.unit),
            ui.tags.td(level, style=f"color:{_status_color(level)}; font-weight:700;"),
            ui.tags.td(", ".join(tr.sources) or "-"),
        ))
    if not rows:
        return ui.div(ui.h4(title), ui.p(empty, style="color:#777;"))
    return ui.div(
        ui.h4(title),
        ui.tags.table(
            {"class": "table table-sm table-striped"},
            ui.tags.thead(ui.tags.tr(*[
                ui.tags.th(x) for x in ("量", "値", "単位", "判定", "根拠")
            ])),
            ui.tags.tbody(*rows),
        ),
    )


def _all_scalar_traces(b, plasma_results, chem_results, spec_traces) -> list:
    all_traces = []
    if b:
        all_traces.extend([tr for tr in b.as_list() if tr.scalar() is not None])
    all_traces.extend([tr for tr in plasma_results if tr.scalar() is not None])
    all_traces.extend([tr for tr in chem_results if tr.scalar() is not None])
    all_traces.extend([tr for tr in spec_traces if tr.scalar() is not None])
    return all_traces


def _trace_researcher_summary(traces: list) -> ui.TagList:
    alerts = [tr for tr in traces if status_label(tr) in {"warning", "error", "notice"}]
    important = important_traces(traces)[:8]
    paper = paper_candidate_traces(traces)[:10]
    alert_panel = _kpi_table("重要警告・注意", alerts[:8], empty="警告・注意はありません。")
    important_panel = _kpi_table("油合成・装置判断 KPI", important,
                                 empty="主要 KPI は計算後に表示されます。")
    paper_panel = _kpi_table("論文・研究ノートに載せる候補値", paper,
                             empty="候補値は計算後に表示されます。")
    formula_cards = []
    for tr in important[:6]:
        formula_cards.append(ui.tags.details(
            ui.tags.summary(f"{tr.name}: {display_value(tr)} {tr.unit}",
                            style="cursor:pointer; font-weight:700;"),
            ui.p(ui.HTML(fr"$$ {tr.equation_latex} $$")),
            *([ui.p(ui.HTML(fr"$$ {tr.substitution_latex} $$"))]
              if tr.substitution_latex else []),
            style=("border:1px solid #e5e7eb; border-radius:6px; padding:8px 10px; "
                   "margin:6px 0; background:white;"),
        ))
    return ui.div(
        ui.div(
            alert_panel,
            important_panel,
            paper_panel,
            style="display:grid; grid-template-columns:repeat(3, minmax(260px, 1fr)); gap:14px;",
        ),
        ui.h4("主要 KPI の計算式ショートカット", style="margin-top:18px;"),
        *(formula_cards or [ui.p("計算後に式が表示されます。", style="color:#777;")]),
        style=("background:#f8fafc; border:1px solid #d9e2ec; border-radius:8px; "
               "padding:14px; margin-bottom:14px;"),
    )


def _render_trace_categorized(traces: list) -> ui.TagList:
    """Group traces by category + render each group as a collapsible section."""
    groups: dict[str, list] = {}
    for tr in traces:
        groups.setdefault(getattr(tr, "category", "other"), []).append(tr)

    order = ["electrical", "plasma", "chemistry", "operational", "other"]
    sections = []
    for cat in order:
        if cat not in groups:
            continue
        label, color = _CATEGORY_META.get(cat, ("その他", "#666"))
        items = groups[cat]
        # sort by anomaly severity: error > warning > notice > ok
        sev_rank = {"error": 0, "warning": 1, "notice": 2, "ok": 3}
        items.sort(key=lambda t: sev_rank.get(
            (t.anomaly.level if t.anomaly else "ok"), 3))
        sections.append(ui.tags.details(
            ui.tags.summary(
                ui.HTML(f"<strong style='color:{color}; font-size:1.1em;'>"
                        f"{label}</strong> "
                        f"<span style='color:#666'>({len(items)})</span>"),
                style="cursor:pointer; padding:8px 0;",
            ),
            *[trace_to_html(t, compact=True) for t in items],
            **{"open": ""},
            style=(f"margin:12px 0; padding:0 8px; "
                   f"border-top:2px solid {color}33;"),
        ))
    return ui.TagList(*sections)


_CSV_FORMAT_EXAMPLE = """# meta: date=2026-04-23, pulse_width_us=0.281, liquid=water, gas=CO2
time_s,voltage_V,current_A
-2.000000e-05,-120.0,0.02
-1.999800e-05,-118.0,0.01
-1.999600e-05,-115.0,0.00
... （1 万行以上のサンプル）"""

_FORMAT_SPEC_PANEL = ui.div(
    ui.h4("📋 STEP 1 — CSV の形式仕様"),
    ui.p("この計算ソフトは以下のフォーマットの CSV のみ受け付けます。"
         "仕様を守らないとバリデータ（STEP 2）が赤エラーで停止します。"),
    ui.tags.pre(
        _CSV_FORMAT_EXAMPLE,
        style=("background:#1e1e1e; color:#e0e0e0; padding:12px; "
               "border-radius:6px; font-family:Menlo,monospace; font-size:0.85em; "
               "overflow-x:auto;"),
    ),
    ui.tags.details(
        ui.tags.summary("▼ 詳しい仕様と注意点", style="cursor:pointer; font-weight:600;"),
        ui.tags.ul(
            ui.tags.li("【必須列】time_s（秒）, voltage_V（V）, current_A（A） — 全て SI 単位"),
            ui.tags.li("列名は英字小文字、間に スペース / 全角文字 を入れない"),
            ui.tags.li("先頭 `#` で始まる行はメタデータ（key=value カンマ区切り）"),
            ui.tags.li("時間は単調増加（負値 OK、オシロのトリガ相対時刻）"),
            ui.tags.li("Δt は一定間隔を推奨。ばらつき CV > 5 % で警告"),
            ui.tags.li("行数: 10 行以上 100,000 行以下（超過時はダウンサンプル推奨）"),
            ui.tags.li("単位: mV → V、mA → A に事前変換してください。列は V / A 固定"),
        ),
        ui.p("❌ NG 例", style="color:#c33; margin-top:10px; font-weight:600;"),
        ui.tags.ul(
            ui.tags.li("time, V, I  ← 列名が仕様と違う"),
            ui.tags.li("time_s,voltage_mV,...  ← mV 単位が違反"),
            ui.tags.li("先頭が空白行  ← 読み込み失敗"),
        ),
    ),
    style=("border:1px solid #dadce0; border-radius:8px; padding:16px; "
           "margin-bottom:16px; background:#f8f9fa;"),
)


app_ui = ui.page_navbar(
    ui.nav_panel(
        "Upload",
        ui.layout_sidebar(
            ui.sidebar(
                ui.h3("データ選択"),
                ui.input_radio_buttons(
                    "source_kind", "入力タイプ",
                    {"xlsx_default": "既存 xlsx (同梱デモ)",
                     "xlsx_path":    "別の xlsx パス",
                     "csv_upload":   "CSV アップロード（推奨）"},
                    selected="xlsx_default",
                ),
                ui.panel_conditional(
                    "input.source_kind == 'xlsx_path'",
                    ui.input_text("xlsx_path", "xlsx パス", str(DEFAULT_XLSX)),
                ),
                ui.panel_conditional(
                    "input.source_kind == 'csv_upload'",
                    ui.input_file("csv_upload", "📤 CSV をアップロード",
                                  accept=[".csv"], multiple=False,
                                  button_label="ファイル選択",
                                  placeholder="ドラッグ or クリック"),
                ),
                ui.panel_conditional(
                    "input.source_kind != 'csv_upload'",
                    ui.input_select("sheet", "xlsx シート（PW 条件）", choices=[]),
                ),
                ui.tags.hr(),
                ui.h5("解析オプション"),
                ui.input_numeric("prf_hz",
                                 "パルス繰返し周波数 f [Hz] (Lissajous 用)",
                                 value=10000, min=1),
                ui.input_checkbox("preproc_offset",
                                  "DC オフセット補正を自動適用", value=True),
                ui.input_checkbox("preproc_align",
                                  "時間軸を最初の V 立ち上がりにそろえる", value=False),
                ui.input_radio_buttons(
                    "plot_mode", "図表モード",
                    {"screen": "Screen（解析用）", "paper": "Paper（論文補助図）"},
                    selected="screen",
                ),
                ui.tags.hr(),
                ui.h5("投入電力の外部チェック用（任意）"),
                ui.input_numeric("socket_power_w",
                                 "コンセント側総消費電力 [W]（0 で無視）",
                                 value=0, min=0),
                ui.p(ui.tags.small(
                    "設備全体の消費電力を入れておくと、解析後に『プラズマ投入電力の"
                    "割合 = P̄ / W_socket』を自動計算し Electrical タブで確認できます。"),
                    style="color:#555;"),
                ui.tags.hr(),
                ui.input_action_button("load_btn", "読み込む & 計算",
                                       class_="btn-primary"),
                width=370,
            ),
            ui.div(
                _FORMAT_SPEC_PANEL,
                ui.h4("📊 STEP 2 — 読み込み結果とバリデーション"),
                ui.output_ui("upload_summary"),
                ui.output_ui("validation_report"),
                ui.h4("🚀 STEP 3 — 次にすること",
                      style="margin-top:24px;"),
                ui.output_ui("next_actions"),
            ),
        ),
    ),
    ui.nav_panel(
        "Waveform",
        ui.tags.details(
            ui.tags.summary("▼ このタブの読み方", style="cursor:pointer; font-weight:600;"),
            ui.tags.ul(
                ui.tags.li("青線 V(t): 電極に印加した電圧波形"),
                ui.tags.li("赤線 I(t): 放電で流れた電流波形"),
                ui.tags.li("横軸 = 時間 [μs]、マウスドラッグで拡大可能"),
                ui.tags.li("V と I のピーク時間差がほぼ無い ⇔ 抵抗性負荷、"
                           "遅延あり ⇔ 誘導性／容量性成分あり"),
                ui.tags.li("正負がほぼ対称 ⇔ 双極性駆動、"
                           "片側に偏り ⇔ 整流性成分あり"),
            ),
            style=("background:#eef5fa; border-radius:6px; padding:12px; "
                   "margin:8px 0;"),
        ),
        output_widget("waveform_plot"),
    ),
    ui.nav_panel(
        "Electrical",
        ui.tags.details(
            ui.tags.summary("▼ このタブの読み方", style="cursor:pointer; font-weight:600;"),
            ui.tags.ul(
                ui.tags.li("下の表は Vpp / Ipp / 平均電力 / 実効値などを一覧表示"),
                ui.tags.li("左プロット P(t): 各時刻の瞬時電力。"
                           "ピークが鋭く立つ ⇔ パルス放電成立"),
                ui.tags.li("右プロット Lissajous: V-q 平面。"
                           "閉ループの面積 = 1 周期エネルギー"),
                ui.tags.li("⚠ 警告: P̄ は「観測窓」の時間平均。実 PRF と窓長の関係に注意。"
                           "Sidebar の PRF を正しく設定するとLissajous 平均電力と比較できる。"),
            ),
            style=("background:#eef5fa; border-radius:6px; padding:12px; "
                   "margin:8px 0;"),
        ),
        ui.row(
            ui.column(6, output_widget("power_plot")),
            ui.column(6, output_widget("lissajous_plot")),
        ),
        ui.output_ui("electrical_table"),
        ui.output_ui("socket_power_comparison"),
    ),
    ui.nav_panel(
        "FFT",
        ui.tags.details(
            ui.tags.summary("▼ このタブの読み方", style="cursor:pointer; font-weight:600;"),
            ui.tags.ul(
                ui.tags.li("両対数軸で V・I のパワースペクトルを表示"),
                ui.tags.li("ピーク周波数 = 駆動源（RF 27 MHz / MW 2.45 GHz 等）"),
                ui.tags.li("2f, 3f の高調波が出る ⇔ プラズマ形成による非線形応答"),
                ui.tags.li("⚠ 注意: Nyquist = f_s/2 = 250 MHz を超える成分は信用しない"),
            ),
            style=("background:#eef5fa; border-radius:6px; padding:12px; "
                   "margin:8px 0;"),
        ),
        output_widget("fft_plot"),
    ),
    ui.nav_panel(
        "Plasma",
        ui.tags.details(
            ui.tags.summary("▼ このタブの読み方", style="cursor:pointer; font-weight:600;"),
            ui.tags.ul(
                ui.tags.li("左: 発光分光 (OES) 測定からの強度比・線幅を入力 → Te, ne を推定"),
                ui.tags.li("Boltzmann 2 本線法: 2 本の強度比から Te。誤差 ±30 % 程度"),
                ui.tags.li("Stark 広がり法: Hα の FWHM [nm] から ne"),
                ui.tags.li("【典型値】Te = 0.5〜5 eV、ne = 10²¹〜10²⁴ m⁻³"),
                ui.tags.li("⚠ 注意: Paschen は気相前提。液中は経験補正必要（Seepersad 2013）"),
                ui.tags.li("n ≥ 3 本でより精度の高い Boltzmann plot → 「励起温度 Te」タブへ"),
            ),
            style=("background:#eef5fa; border-radius:6px; padding:12px; margin:8px 0;"),
        ),
        ui.layout_sidebar(
            ui.sidebar(
                ui.h4("Boltzmann plot 入力（発光分光）"),
                ui.input_numeric("I_ij", "I_ij", 1.0),
                ui.input_numeric("I_kl", "I_kl", 0.5),
                ui.input_numeric("g_i", "g_i", 6),
                ui.input_numeric("g_k", "g_k", 8),
                ui.input_numeric("A_ij", "A_ij [1/s]", 4.4e7),
                ui.input_numeric("A_kl", "A_kl [1/s]", 8.4e6),
                ui.input_numeric("nu_ij", "ν_ij [Hz]", 4.57e14),
                ui.input_numeric("nu_kl", "ν_kl [Hz]", 6.17e14),
                ui.input_numeric("E_i", "E_i [eV]", 12.09),
                ui.input_numeric("E_k", "E_k [eV]", 12.75),
                ui.h4("Stark (Hα FWHM)"),
                ui.input_numeric("fwhm_nm", "Δλ_{1/2} [nm]", 0.5),
                ui.input_numeric("alpha_stark", "α (m^-3·nm^-1.5)", 1.0e23),
                ui.h4("Ohmic"),
                ui.input_numeric("sigma_liquid", "σ [S/m]", 0.01),
                ui.input_numeric("E_field", "E [V/m]", 1e6),
                ui.input_numeric("T_gas_K", "T_gas [K]（非平衡診断）", 300, min=1),
                ui.h4("Paschen"),
                ui.input_numeric("p_gas", "p [Pa]", 101325),
                ui.input_numeric("d_gap_mm", "d [mm]", 1.0),
                ui.input_action_button("plasma_btn", "計算", class_="btn-primary"),
                width=360,
            ),
            ui.output_ui("plasma_output"),
        ),
    ),
    ui.nav_panel(
        "Chemistry",
        ui.tags.details(
            ui.tags.summary("▼ このタブの読み方", style="cursor:pointer; font-weight:600;"),
            ui.tags.ul(
                ui.tags.li("GC / GC-MS で定量した生成モル数と ΔH（反応エンタルピー）から"
                           "G 値と化学効率 η を算出"),
                ui.tags.li("E_plasma は Electrical タブの吸収エネルギー E を自動で使う"),
                ui.tags.li("【典型値】G = 1〜10 molecules/100 eV、η = 5〜15 %"),
                ui.tags.li("⚠ 注意: E_plasma は観測窓のエネルギー。PRF を掛けた実効値は別計算"),
            ),
            style=("background:#eef5fa; border-radius:6px; padding:12px; margin:8px 0;"),
        ),
        ui.layout_sidebar(
            ui.sidebar(
                ui.h4("GC 測定入力"),
                ui.input_numeric("n_prod_mol", "生成モル数 [mol]", 1e-6),
                ui.input_numeric("n_co2_in_mol", "CO₂ 入口モル数 [mol]", 1e-4),
                ui.input_numeric("n_co2_out_mol", "CO₂ 出口モル数 [mol]", 9e-5),
                ui.input_numeric("delta_H", "ΔH [kJ/mol]", 286,
                                 min=0),
                ui.tags.hr(),
                ui.h5("ASF 炭素数分布（任意）"),
                ui.input_numeric("asf_c1", "C1 weight fraction", 0.5, min=0),
                ui.input_numeric("asf_c2", "C2 weight fraction", 0.25, min=0),
                ui.input_numeric("asf_c3", "C3 weight fraction", 0.12, min=0),
                ui.input_numeric("asf_c4", "C4+ weight fraction", 0.06, min=0),
                ui.input_action_button("chem_btn", "計算", class_="btn-primary"),
                ui.tags.hr(),
                ui.p("E_plasma は Electrical タブの P̄×T を自動流用。"),
                width=320,
            ),
            ui.output_ui("chem_output"),
        ),
    ),
    ui.nav_panel(
        "励起温度 Te",
        ui.tags.details(
            ui.tags.summary("▼ このタブの読み方（LTE 直線性判定つき）",
                            style="cursor:pointer; font-weight:600;"),
            ui.tags.ul(
                ui.tags.li("元素を選択 → 発光線の強度を入力 → Boltzmann プロットから Te 推定"),
                ui.tags.li("強度 0 の線は除外される（xlsx と同じ挙動）"),
                ui.tags.li("n ≥ 3 本推奨。2 本では誤差が大"),
                ui.tags.li("プロット右上の R² が 0.95 以上 ⇔ LTE 成立 確度高い"),
                ui.tags.li("R² < 0.85 ⇔ LTE 非成立を疑う（線選択 or 感度校正 見直し）"),
                ui.tags.li("野村研究室で推奨: タングステン電極 + 4 本線（下準位 6s 共通）"),
            ),
            style=("background:#eef5fa; border-radius:6px; padding:12px; margin:8px 0;"),
        ),
        ui.layout_sidebar(
            ui.sidebar(
                ui.h4("発光分光 強度入力"),
                ui.input_select("spec_element", "対象元素",
                                choices={e: e for e in list_elements()},
                                selected="H"),
                ui.tags.hr(),
                ui.input_file("spec_csv", "強度 CSV アップロード（任意）",
                              accept=[".csv"]),
                ui.p(ui.tags.small(
                    "CSV 形式: `line,intensity` 1 列ペア、または "
                    "`element,line,intensity` 3 列。先頭 `# meta: ...` 可。")),
                ui.tags.hr(),
                ui.output_ui("spec_inputs"),
                ui.input_action_button("spec_btn", "Te 計算",
                                       class_="btn-primary"),
                width=360,
            ),
            ui.row(
                ui.column(6, output_widget("boltzmann_plot")),
                ui.column(6, ui.output_ui("spec_output")),
            ),
        ),
    ),
    ui.nav_panel(
        "🌡 Thermo DB",
        ui.tags.details(
            ui.tags.summary("▼ このタブの読み方",
                            style="cursor:pointer; font-weight:600;"),
            ui.tags.ul(
                ui.tags.li("species 名を入力 → NASA polynomial 由来の Cp(T), H(T), S(T), G(T) を表示"),
                ui.tags.li("典型物質: CO2, H2, H2O, CO, CH3OH, CH4, OH, O, H, NO ほか 1100+"),
                ui.tags.li("Tmin / Tmax の範囲外は赤帯で警告。Wilhoit 高温外挿に切替可"),
                ui.tags.li("出典: NASA Glenn 2002 (NASA9), GRI-Mech 3.0 (NASA7), CEA"),
            ),
            style=("background:#eef5fa; border-radius:6px; padding:12px; margin:8px 0;"),
        ),
        ui.layout_sidebar(
            ui.sidebar(
                ui.h4("species を選ぶ"),
                ui.input_text("thermo_species", "species 名", value="CO2"),
                ui.input_numeric("thermo_T", "T [K]", 1000, min=10),
                ui.input_action_button("thermo_btn", "計算", class_="btn-primary"),
                width=320,
            ),
            ui.output_ui("thermo_output"),
        ),
    ),
    ui.nav_panel(
        "⚖️ Equilibrium",
        ui.tags.details(
            ui.tags.summary("▼ このタブの読み方",
                            style="cursor:pointer; font-weight:600;"),
            ui.tags.ul(
                ui.tags.li("CEA 風 TP / HP / UV 平衡計算"),
                ui.tags.li("元素入力: C, H, O, N の各モル数 → 平衡組成（mole fraction）"),
                ui.tags.li("凝縮相判定: 黒鉛 (C(gr)) や金属酸化物 (CuO, WO3 等) の析出可否を自動表示"),
                ui.tags.li("⚠ 算出された Te が Te-provisional の場合は使わない"),
            ),
            style=("background:#eef5fa; border-radius:6px; padding:12px; margin:8px 0;"),
        ),
        ui.layout_sidebar(
            ui.sidebar(
                ui.h4("平衡計算 (TP)"),
                ui.input_text("eq_species",
                              "species (カンマ区切り)",
                              value="CO2,H2,CO,H2O,CH3OH,OH,H,O"),
                ui.input_numeric("eq_T", "T [K]", 2000.0, min=100),
                ui.input_numeric("eq_P_atm", "P [atm]", 1.0, min=0.001),
                ui.input_numeric("eq_C", "C モル数", 1.0, min=0),
                ui.input_numeric("eq_H", "H モル数", 2.0, min=0),
                ui.input_numeric("eq_O", "O モル数", 2.0, min=0),
                ui.input_checkbox("eq_condensed",
                                  "凝縮相 (graphite/oxides) を試す", value=True),
                ui.input_action_button("eq_btn", "計算", class_="btn-primary"),
                width=320,
            ),
            ui.output_ui("eq_output"),
        ),
    ),
    ui.nav_panel(
        "🛤 Reaction Path",
        ui.tags.details(
            ui.tags.summary("▼ このタブの読み方",
                            style="cursor:pointer; font-weight:600;"),
            ui.tags.ul(
                ui.tags.li("Equilibrium タブで計算した species を Cantera YAML に export"),
                ui.tags.li("Cantera がインストールされていれば ReactionPathDiagram を生成"),
                ui.tags.li("元素 (C / H / O) ごとのフラックス図を可視化"),
                ui.tags.li("Cantera 未導入時は YAML テキストのみ出力"),
            ),
            style=("background:#eef5fa; border-radius:6px; padding:12px; margin:8px 0;"),
        ),
        ui.layout_sidebar(
            ui.sidebar(
                ui.h4("Cantera YAML エクスポート"),
                ui.input_text("rp_species",
                              "species (カンマ区切り)",
                              value="CO2,H2,CO,H2O,CH3OH,OH"),
                ui.input_action_button("rp_btn", "YAML 生成", class_="btn-primary"),
                ui.tags.hr(),
                ui.tags.small(
                    "M4 Mac でも import cantera は可能 (pip install cantera)。",
                    style="color:#666;"),
                width=320,
            ),
            ui.output_ui("rp_output"),
        ),
    ),
    ui.nav_panel(
        "Trace",
        ui.tags.details(
            ui.tags.summary("▼ このタブの読み方", style="cursor:pointer; font-weight:600;"),
            ui.tags.ul(
                ui.tags.li("全物理量のカードをアコーディオンで一覧表示"),
                ui.tags.li("各カードは 3 段階の解説 (🔰 初学者 / 🔬 研究者 / 🎓 博士) を内包"),
                ui.tags.li("カード左辺の色がエラーラインの判定結果を示す: "
                           "緑=正常 / 青=注意 / 黄=警告 / 赤=異常"),
                ui.tags.li("警告・異常時は「可能性のある原因」と「参照論文」が自動表示"),
                ui.tags.li("「📐 理論式（展開）」 を開くと式と数値代入が見える"),
            ),
            style=("background:#eef5fa; border-radius:6px; padding:12px; margin:8px 0;"),
        ),
        ui.output_ui("trace_all"),
    ),
    ui.nav_panel(
        "Export",
        ui.download_button("dl_md", "Markdown レポートをダウンロード"),
        ui.download_button("dl_csv", "解析済み量 CSV をダウンロード"),
        ui.p("CSV は quantity,value,unit,status,source,equation_key 形式です。"
             "元波形CSVではなく、論文補助表に使う計算済み量を出力します。",
             style="color:#555; margin-top:8px;"),
    ),
    title="液中プラズマ オシロスコープ解析",
    header=MATH_HEADER,
)


def server(input, output, session):
    from oscillo_plasma_calc.signal.preprocess import preprocess as _preprocess
    current = reactive.value(None)      # Waveform
    bundle = reactive.value(None)       # AnalysisBundle
    validation = reactive.value(None)   # ValidationReport | None

    @reactive.effect
    def _populate_sheets():
        kind = input.source_kind()
        if kind == "csv_upload":
            return
        path = DEFAULT_XLSX if kind == "xlsx_default" else Path(input.xlsx_path())
        if path and path.exists() and path.suffix.lower() == ".xlsx":
            try:
                from oscillo_plasma_calc.io_layer.xlsx_loader import list_xlsx_sheets
                sheets = [s for s in list_xlsx_sheets(path) if s.startswith("PW目盛")]
                if sheets:
                    ui.update_select("sheet", choices=sheets, selected=sheets[0])
            except Exception:
                pass

    @reactive.effect
    @reactive.event(input.load_btn)
    def _load():
        kind = input.source_kind()
        validation.set(None)
        try:
            if kind == "csv_upload":
                fi = input.csv_upload()
                if not fi:
                    ui.notification_show(
                        "CSV がアップロードされていません。"
                        "STEP 2（ファイル選択）を先に実行してください。",
                        type="error")
                    return
                path = fi[0]["datapath"]
                # run validator first
                rep = validate_csv(path)
                validation.set(rep)
                if not rep.passed:
                    ui.notification_show(
                        "❌ 形式エラー: 計算停止。詳細は STEP 2 を確認。",
                        type="error")
                    current.set(None)
                    bundle.set(None)
                    return
                wf = load_csv(path, label=Path(fi[0]["name"]).stem)
            else:
                path = DEFAULT_XLSX if kind == "xlsx_default" else Path(input.xlsx_path())
                sheet = input.sheet() or None
                wfs = load_xlsx(path, sheet_name=sheet)
                if not wfs:
                    ui.notification_show("シートが見つかりません", type="error")
                    return
                wf = wfs[0]
        except Exception as e:
            ui.notification_show(f"読み込み失敗: {e}", type="error")
            return

        # preprocessing（会議 2026-04-23: DC オフセット補正を推奨）
        wf = _preprocess(
            wf,
            remove_offset=bool(input.preproc_offset()),
            align_edge=bool(input.preproc_align()),
        )
        current.set(wf)
        bundle.set(analyze_electrical(wf, pulse_rep_freq_hz=float(input.prf_hz())))
        ui.notification_show(
            f"✓ 読み込み完了: {wf.label} (N={wf.n}, Δt={wf.dt*1e9:.2f} ns)",
            type="message")

    @output
    @render.ui
    def upload_summary():
        wf = current.get()
        b = bundle.get()
        if wf is None:
            return ui.div(
                ui.p("まだデータが読み込まれていません。"),
                ui.p("左サイドバーでデータを選んで「読み込む & 計算」を押してください。",
                     style="color:#666;"),
                style="padding:10px 0;",
            )
        vpp = wf.v.max()-wf.v.min(); ipp = wf.i.max()-wf.i.min()
        baseline_n = max(1, int(wf.n * 0.02))
        v_offset = float(np.mean(wf.v[:baseline_n]))
        i_offset = float(np.mean(wf.i[:baseline_n]))
        prf = float(input.prf_hz())
        budget_margin = b.budget.scalar() if b and b.budget else None
        meta_items = [ui.tags.li(f"{k}: {v}") for k, v in wf.meta.items()]
        cards = [
            ("Samples", f"{wf.n:,}", "N"),
            ("Δt / fs", f"{wf.dt*1e9:.3f} ns / {wf.fs/1e6:.1f} MHz", "sampling"),
            ("Window", f"{wf.duration*1e6:.3f} μs", "T"),
            ("Vpp", f"{vpp/1000:.3f} kV", "voltage"),
            ("Ipp", f"{ipp:.3g} A", "current"),
            ("PRF", f"{prf:.4g} Hz", "input"),
            ("DC offset", f"V {v_offset:.3g} / I {i_offset:.3g}", "pre-trigger"),
            ("Budget margin", f"{budget_margin:.3g} %" if budget_margin is not None else "-", "1 kW rule"),
        ]
        return ui.div(
            ui.div(
                ui.h5(f"📁 {wf.label}",
                      style="color:#1a7f37; margin-bottom:6px;"),
                ui.div(
                    *[ui.div(
                        ui.div(label, style="color:#667085; font-size:0.82em;"),
                        ui.div(value, style="font-size:1.15em; font-weight:700;"),
                        ui.div(note, style="color:#667085; font-size:0.78em;"),
                        style=("background:white; border:1px solid #d7e3d8; border-radius:6px; "
                               "padding:10px 12px; min-height:84px;"),
                    ) for label, value, note in cards],
                    style=("display:grid; grid-template-columns:repeat(4, minmax(150px, 1fr)); "
                           "gap:10px; margin:10px 0;"),
                ),
                ui.tags.details(
                    ui.tags.summary("メタデータ詳細"),
                    ui.tags.ul(*meta_items),
                ),
                style=("background:#e8f5ea; border-left:3px solid #1a7f37; "
                       "padding:12px 16px; border-radius:4px; margin:8px 0;"),
            ),
        )

    @output
    @render.ui
    def validation_report():
        rep = validation.get()
        if rep is None:
            return ""
        rows = []
        for item in rep.hard_errors:
            rows.append(ui.div(
                ui.tags.strong("✗ エラー"), " — ", item.message,
                *([ui.tags.br(), ui.tags.small(f"💡 対処: {item.hint}",
                                                style="color:#555;")]
                  if item.hint else []),
                style=("background:#fdeaea; border-left:3px solid #c33; "
                       "padding:10px 14px; margin:6px 0; border-radius:4px;")))
        for item in rep.warnings:
            rows.append(ui.div(
                ui.tags.strong("⚠ 警告"), " — ", item.message,
                *([ui.tags.br(), ui.tags.small(f"💡 {item.hint}",
                                                style="color:#555;")]
                  if item.hint else []),
                style=("background:#fff7e6; border-left:3px solid #c98a00; "
                       "padding:10px 14px; margin:6px 0; border-radius:4px;")))
        for item in rep.notices:
            rows.append(ui.div(
                ui.tags.strong("ℹ 情報"), " — ", item.message,
                *([ui.tags.br(), ui.tags.small(f"💡 {item.hint}",
                                                style="color:#555;")]
                  if item.hint else []),
                style=("background:#e8f0fa; border-left:3px solid #3a7bd5; "
                       "padding:10px 14px; margin:6px 0; border-radius:4px;")))
        for item in rep.ok_items:
            rows.append(ui.div(
                ui.tags.strong("✓"), " ", item.message,
                style=("background:#e8f5ea; border-left:3px solid #1a7f37; "
                       "padding:6px 14px; margin:3px 0; border-radius:4px; "
                       "font-size:0.9em;")))
        return ui.div(
            ui.h5("バリデーション結果"),
            *rows,
            style="margin:12px 0;",
        )

    @output
    @render.ui
    def next_actions():
        wf = current.get()
        b = bundle.get()
        if wf is None:
            return ui.p("データ読み込み後、次のステップが表示されます。",
                        style="color:#888;")
        traces = b.as_list() if b else []
        alerts = [tr for tr in traces if status_label(tr) in {"warning", "error"}]
        action_items = []
        if alerts:
            action_items.append("【Trace】警告・異常のみフィルタで原因候補と根拠論文を確認")
        if b and b.v_rise.anomaly and b.v_rise.anomaly.level in {"warning", "error"}:
            action_items.append("【Waveform】立ち上がり注釈を拡大し、プローブ帯域とトリガ位置を確認")
        if b and b.budget and b.budget.anomaly and b.budget.anomaly.level in {"warning", "error"}:
            action_items.append("【Electrical】P(t)、Duty、Ppeak·D を見直し、1 kW 予算を確認")
        action_items.extend([
            "【Electrical】P(t)・累積E(t)・Lissajousを比較",
            "【FFT】支配周波数と高調波、Nyquist線を確認",
            "【Chemistry】GC値を入れて G値・SEI・油化KPI を算出",
            "【Export】Markdown / 解析済み量CSV を保存",
        ])
        return ui.div(
            ui.p("✓ データ読み込み成功。優先順に以下を確認してください:",
                 style="color:#1a7f37; font-weight:600;"),
            ui.tags.ol(*[ui.tags.li(item) for item in action_items]),
            style="padding:8px 0;",
        )

    @output
    @render.ui
    def socket_power_comparison():
        b = bundle.get()
        if b is None:
            return ""
        try:
            sw = float(input.socket_power_w())
        except Exception:
            sw = 0.0
        if sw <= 0:
            return ""
        p_bar = float(b.p_mean.value) if b.p_mean.scalar() is not None else 0.0
        ratio = (p_bar / sw) * 100 if sw > 0 else float("nan")
        return ui.div(
            ui.h5("🔌 コンセント側消費電力との比較（会議 2026-04-23）"),
            ui.tags.ul(
                ui.tags.li(f"コンセント側 W_socket = {sw:.2f} W"),
                ui.tags.li(f"観測窓平均電力 P̄ = {p_bar:.2f} W"),
                ui.tags.li(f"プラズマ投入割合 P̄ / W_socket ≈ {ratio:.2f} %"),
            ),
            ui.p("割合が 70 〜 95 % 程度なら妥当。顕著に低ければ装置の待機電力が大きい、"
                 "超過なら観測窓 / PRF の見直し推奨。",
                 style="color:#555; font-size:0.9em;"),
            style=("background:#f3f7fb; border-left:3px solid #3a7bd5; "
                   "padding:12px 16px; border-radius:4px; margin-top:12px;"),
        )

    @output
    @render_widget
    def waveform_plot():
        wf = current.get()
        if wf is None:
            return go.Figure()
        mode = input.plot_mode()
        ann = waveform_annotations(wf.t, wf.v, wf.i)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=wf.t*1e6, y=wf.v, name="V(t) [V]",
                                 line=dict(color="#2a6fb0")))
        fig.add_trace(go.Scatter(x=wf.t*1e6, y=wf.i, name="I(t) [A]",
                                 yaxis="y2", line=dict(color="#d64545")))
        if ann:
            fig.add_vline(x=ann["t10_us"], line_dash="dot", line_color="#6b7280",
                          annotation_text="10% rise")
            fig.add_vline(x=ann["t90_us"], line_dash="dot", line_color="#111827",
                          annotation_text="90% rise")
            fig.add_vline(x=ann["t_zero_us"], line_dash="dash", line_color="#8a6d3b",
                          annotation_text="zero cross")
            fig.add_trace(go.Scatter(
                x=[ann["t_vmax_us"], ann["t_vmin_us"]],
                y=[ann["vmax"], ann["vmin"]],
                mode="markers+text",
                text=["Vmax", "Vmin"],
                textposition="top center",
                marker=dict(size=9, color="#2a6fb0"),
                name="V peaks",
            ))
            fig.add_trace(go.Scatter(
                x=[ann["t_imax_us"]],
                y=[ann["imax"]],
                mode="markers+text",
                text=["|I|max"],
                textposition="bottom center",
                marker=dict(size=9, color="#d64545", symbol="diamond"),
                name="I peak",
                yaxis="y2",
            ))
        fig.update_layout(
            title=f"Waveform — {wf.label}",
            xaxis_title="time [μs]",
            yaxis=dict(title="V [V]"),
            yaxis2=dict(title="I [A]", overlaying="y", side="right"),
            height=500,
        )
        return apply_research_plot_layout(fig, mode)

    @output
    @render_widget
    def power_plot():
        b = bundle.get()
        if b is None:
            return go.Figure()
        mode = input.plot_mode()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=b.waveform.t*1e6, y=b.p_inst.value,
                                 name="P(t) [W]", line=dict(color="#2a6fb0")))
        e_cum = b.energy.extra.get("E_cumulative")
        if e_cum is not None:
            fig.add_trace(go.Scatter(
                x=b.waveform.t*1e6, y=e_cum,
                name="E(t) cumulative [J]",
                yaxis="y2",
                line=dict(color="#1a7f37"),
            ))
        if b.p_peak.scalar() is not None:
            fig.add_hline(y=b.p_peak.scalar(), line_dash="dot", line_color="#c98a00",
                          annotation_text="|P|max")
        fig.update_layout(title="Instantaneous power P(t) = V·I",
                          xaxis_title="time [μs]",
                          yaxis=dict(title="P [W]"),
                          yaxis2=dict(title="E cumulative [J]", overlaying="y", side="right"),
                          height=420)
        return apply_research_plot_layout(fig, mode)

    @output
    @render_widget
    def lissajous_plot():
        b = bundle.get()
        if b is None:
            return go.Figure()
        mode = input.plot_mode()
        q = b.lissajous.extra["q"]
        fig = go.Figure(go.Scatter(x=q*1e9, y=b.waveform.v, mode="lines",
                                   line=dict(color="#7a4fb0"), name="V-q loop"))
        area = b.lissajous.extra.get("loop_area_J")
        if area is not None:
            fig.add_annotation(
                xref="paper", yref="paper", x=0.02, y=0.98, showarrow=False,
                align="left",
                text=f"loop area = {area:.4g} J/cycle<br>f = {b.lissajous.extra.get('f_hz', float('nan')):.4g} Hz",
                bgcolor="rgba(255,255,255,0.8)",
            )
        fig.update_layout(title="Lissajous (V vs q)",
                          xaxis_title="q [nC]", yaxis_title="V [V]",
                          height=420)
        return apply_research_plot_layout(fig, mode)

    @output
    @render_widget
    def fft_plot():
        wf = current.get()
        if wf is None:
            return go.Figure()
        mode = input.plot_mode()
        freq_v, amp_v = power_spectrum(wf.v, wf.dt)
        freq_i, amp_i = power_spectrum(wf.i, wf.dt)
        # Phase 0 fix: drop DC bin (freq[0]=0) — log scale + 0 makes Plotly
        # auto-range explode to 10^243. Also clip to Nyquist for display.
        nyq_mhz = wf.fs / 2 / 1e6
        v_mhz = freq_v[1:] / 1e6
        i_mhz = freq_i[1:] / 1e6
        v_amp = amp_v[1:]
        i_amp = amp_i[1:]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=v_mhz, y=v_amp, name="V spectrum"))
        fig.add_trace(go.Scatter(x=i_mhz, y=i_amp, name="I spectrum",
                                 yaxis="y2"))
        dom_idx = int(np.nanargmax(v_amp)) if len(v_amp) > 0 else 0
        dom_mhz = float(v_mhz[dom_idx]) if len(v_mhz) > 0 else 0.0
        for mult, color in ((1, "#111827"), (2, "#6b7280"), (3, "#9ca3af")):
            x = dom_mhz * mult
            if x > 0 and x <= nyq_mhz:
                fig.add_vline(x=x, line_dash="dash" if mult == 1 else "dot",
                              line_color=color,
                              annotation_text=f"{mult}f = {x:.3g} MHz")
        fig.add_vline(x=nyq_mhz, line_dash="solid", line_color="#c33333",
                      annotation_text=f"Nyquist {nyq_mhz:.3g} MHz")
        # Lock x range to [first non-DC bin, Nyquist]
        x_min = max(float(v_mhz[0]) if len(v_mhz) else 1e-3, 1e-3)
        fig.update_layout(
            title="Power spectrum (rFFT, DC bin excluded)",
            xaxis=dict(title="frequency [MHz]", type="log",
                       range=[np.log10(x_min), np.log10(nyq_mhz)]),
            yaxis=dict(title="|V| [V]"),
            yaxis2=dict(title="|I| [A]", overlaying="y", side="right"),
            height=500,
        )
        return apply_research_plot_layout(fig, mode)

    @output
    @render.ui
    def electrical_table():
        b = bundle.get()
        if b is None:
            return ui.p("")
        rows = [(tr.name, f"{tr.scalar():.6g}" if tr.scalar() is not None else "array",
                 tr.unit, ", ".join(tr.sources))
                for tr in b.as_list() if tr.name not in {"Instantaneous power P(t)",
                                                          "Instantaneous impedance Z(t)"}]
        header = ui.tags.tr(*[ui.tags.th(x) for x in ("量", "値", "単位", "根拠論文")])
        body = [ui.tags.tr(*[ui.tags.td(c) for c in row]) for row in rows]
        return ui.div(
            ui.h4(f"電気系サマリ — {b.waveform.label}"),
            _kpi_table("電力・エネルギー KPI", [
                b.p_peak, b.energy, b.p_mean, b.lissajous,
                b.pulse_e, b.duty, b.p_eff, b.abs_p_avg, b.budget,
            ]),
            ui.tags.table(
                {"class": "table table-striped"},
                ui.tags.thead(header), ui.tags.tbody(*body),
            ),
            ui.p(f"支配周波数 (V): {b.dominant_freq_v/1e6:.3f} MHz"),
        )

    # ---- Plasma tab ----
    plasma_results = reactive.value([])

    @reactive.effect
    @reactive.event(input.plasma_btn)
    def _plasma_compute():
        res = []
        try:
            res.append(electron_temperature_boltzmann(
                input.I_ij(), input.I_kl(),
                input.g_i(), input.g_k(),
                input.A_ij(), input.A_kl(),
                input.nu_ij(), input.nu_kl(),
                input.E_i(), input.E_k(),
            ))
        except Exception as e:
            ui.notification_show(f"Boltzmann: {e}", type="warning")
        try:
            ne = electron_density_stark(input.fwhm_nm(), alpha=input.alpha_stark())
            res.append(ne)
            te_tr = res[0] if res else None
            if te_tr and te_tr.scalar() and te_tr.scalar() > 0:
                res.append(debye_length(te_tr.scalar(), ne.value))
            res.append(plasma_frequency(ne.value))
        except Exception as e:
            ui.notification_show(f"Stark/Debye: {e}", type="warning")
        try:
            res.append(ohmic_heating_density(input.sigma_liquid(), input.E_field()))
            en = reduced_electric_field(input.E_field(), input.p_gas(), input.T_gas_K())
            res.append(en)
            if en.scalar() and en.scalar() > 0:
                res.append(mean_electron_energy(en.scalar()))
            if res and res[0].scalar() and res[0].scalar() > 0:
                # 2-line Te is eV; convert to K for the non-equilibrium ratio.
                res.append(non_equilibrium_ratio(res[0].scalar() * 11604.518, input.T_gas_K()))
        except Exception as e:
            ui.notification_show(f"Ohmic/non-eq: {e}", type="warning")
        try:
            res.append(paschen_breakdown_voltage(
                input.p_gas(), input.d_gap_mm() * 1e-3))
        except Exception as e:
            ui.notification_show(f"Paschen: {e}", type="warning")
        plasma_results.set([_bind(tr) for tr in res])

    @output
    @render.ui
    def plasma_output():
        res = plasma_results.get()
        if not res:
            return ui.p("左の入力を埋めて「計算」を押してください。")
        diagnostics = [tr for tr in res if tr.explanation_key in {
            "boltzmann_two_line", "stark", "debye", "plasma_freq", "e_over_n",
            "mean_e_energy", "tv_rot_ratio",
        }]
        return ui.div(
            _kpi_table("反応場診断 KPI", diagnostics),
            *[trace_to_html(tr, compact=False) for tr in res],
        )

    # ---- Chemistry tab ----
    chem_results = reactive.value([])

    @reactive.effect
    @reactive.event(input.chem_btn)
    def _chem_compute():
        b = bundle.get()
        if b is None:
            ui.notification_show("先に Electrical タブで波形を読み込んでください",
                                 type="warning")
            return
        E_plasma = b.energy.value
        g = g_value(input.n_prod_mol(), E_plasma)
        eta = chemical_efficiency(input.delta_H(), input.n_prod_mol(), E_plasma)
        sei = specific_energy_input(E_plasma, input.n_co2_in_mol())
        ec = energy_cost(E_plasma, input.n_prod_mol())
        chi = co2_conversion_rate(input.n_co2_in_mol(), input.n_co2_out_mol())
        eta_se = single_pass_energy_efficiency(
            chi.scalar() or float("nan"),
            input.delta_H(),
            sei.scalar() or float("nan"),
        )
        asf = asf_chain_probability({
            1: input.asf_c1(),
            2: input.asf_c2(),
            3: input.asf_c3(),
            4: input.asf_c4(),
        })
        res = [g, eta, sei, ec, chi, eta_se, asf]
        chem_results.set([_bind(tr) for tr in res])

    @output
    @render.ui
    def chem_output():
        res = chem_results.get()
        if not res:
            return ui.p("左の入力を埋めて「計算」を押してください。")
        return ui.div(
            _kpi_table("油化判断 KPI", res),
            *[trace_to_html(tr, compact=False) for tr in res],
        )

    # ---- 励起温度 Te tab ----
    spec_traces = reactive.value([])
    spec_bp = reactive.value(None)
    spec_loaded = reactive.value({})   # {element: {line: intensity}} from CSV

    @output
    @render.ui
    def spec_inputs():
        el = input.spec_element()
        lines = get_lines(el)
        preloaded = spec_loaded.get().get(el, {})
        widgets = [ui.h5(f"{el} 発光線（I=0 で除外）")]
        for ln in lines:
            default = float(preloaded.get(ln.label, 0.0))
            widgets.append(ui.input_numeric(
                f"I_{el}_{ln.label}",
                f"{ln.label}  (λ={ln.wavelength_nm:.3f} nm, E_u={ln.E_upper_eV:.3f} eV)",
                value=default, min=0,
            ))
        return ui.div(*widgets)

    @reactive.effect
    @reactive.event(input.spec_csv)
    def _spec_csv_load():
        fileinfo = input.spec_csv()
        if not fileinfo:
            return
        path = fileinfo[0]["datapath"]
        try:
            grouped, meta = load_intensity_csv(path)
            spec_loaded.set(grouped)
            ui.notification_show(
                f"CSV 読み込み: elements={list(grouped.keys())}, meta={meta}",
                type="message")
        except Exception as e:
            ui.notification_show(f"CSV 読み込み失敗: {e}", type="error")

    @reactive.effect
    @reactive.event(input.spec_btn)
    def _spec_compute():
        el = input.spec_element()
        lines = get_lines(el)
        intensities = {ln.label: float(getattr(input, f"I_{el}_{ln.label}")() or 0.0)
                       for ln in lines}
        try:
            res, tr = excitation_temperature(el, intensities)
            spec_bp.set(res)
            spec_traces.set([_bind(tr)])
            ui.notification_show(
                f"{el}: Te = {res.Te_K:.4g} K  (n={res.n_used})",
                type="message")
        except Exception as e:
            ui.notification_show(f"Te 計算失敗: {e}", type="error")

    @output
    @render_widget
    def boltzmann_plot():
        bp = spec_bp.get()
        fig = go.Figure()
        if bp is None or bp.n_used < 2:
            fig.update_layout(title="Boltzmann plot（データ投入後に表示）",
                              xaxis_title="x = E_u − E_l  [eV]",
                              yaxis_title="y = ln(I / (g A ν))",
                              height=500)
            return fig
        fig.add_trace(go.Scatter(
            x=bp.xs, y=bp.ys, mode="markers+text",
            text=bp.line_labels, textposition="top center",
            marker=dict(size=10, color="#2a6fb0"),
            name="観測点",
        ))
        # fit line
        x_arr = np.array(bp.xs)
        intercept = (sum(bp.ys) - bp.slope * sum(bp.xs)) / bp.n_used
        xs_fit = np.linspace(x_arr.min(), x_arr.max(), 2)
        fig.add_trace(go.Scatter(
            x=xs_fit, y=bp.slope * xs_fit + intercept,
            mode="lines", line=dict(color="#d64545", dash="dash"),
            name=f"fit (slope={bp.slope:.3g}, R²={bp.r_squared:.3f})",
        ))
        color = "#1a7f37" if bp.r_squared >= 0.95 else "#c98a00" if bp.r_squared >= 0.85 else "#c33333"
        provisional = "" if bp.is_te_reliable else " ⚠ 参考値（下流不可）"
        fig.add_annotation(
            xref="paper", yref="paper", x=0.02, y=0.98, showarrow=False,
            align="left",
            text=(f"R² = {bp.r_squared:.4f}<br>n = {bp.n_used}<br>"
                  f"{bp.lte_quality_label}{provisional}"),
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor=color,
        )
        te_label = f"Te={bp.Te_K:.4g} K" if bp.is_te_reliable else f"Te=(参考値) {bp.Te_K:.4g} K"
        fig.update_layout(
            title=f"Boltzmann plot — {bp.element}, {te_label} (n={bp.n_used})",
            xaxis_title="x = E_u − E_l  [eV]",
            yaxis_title="y = ln(I / (g A ν))",
            height=500,
        )
        return apply_research_plot_layout(fig, input.plot_mode())

    @output
    @render.ui
    def spec_output():
        traces = spec_traces.get()
        bp = spec_bp.get()
        if not traces:
            return ui.p("左の入力を埋めて「Te 計算」を押してください。"
                        "CSV をアップロードすれば強度欄が自動で埋まります。")
        parts = [trace_to_html(tr, compact=False) for tr in traces]
        if bp is not None and bp.n_used >= 2:
            if not bp.is_te_reliable:
                # Phase 0.2: provisional banner (downstream computation should be locked)
                parts.insert(0, ui.div(
                    ui.tags.strong("⚠ この Te は参考値です（下流計算には使えません）"),
                    ui.p(bp.reliability_warning, style="margin:6px 0;"),
                    ui.tags.ul(
                        ui.tags.li("採用線が 3 本未満、または E_u 差が小さすぎる可能性"),
                        ui.tags.li("強度 0、自己吸収、感度補正不足、線ラベル違いを確認"),
                        ui.tags.li("タングステン電極の 4 本線（下準位 6s 共通）が推奨"),
                    ),
                    style=("background:#fdeaea; border-left:4px solid #c33333; "
                           "padding:12px 16px; border-radius:6px; "
                           "margin-bottom:12px; color:#7a1c1c;"),
                ))
            else:
                parts.insert(0, ui.div(
                    ui.tags.strong("✓ この Te は信頼できます"),
                    ui.p(f"R² = {bp.r_squared:.3f} ≥ 0.85, "
                         f"採用線数 = {bp.n_used} ≥ 3 → 下流計算で使用可。",
                         style="margin:6px 0;"),
                    style=("background:#e8f5ea; border-left:4px solid #1a7f37; "
                           "padding:12px 16px; border-radius:6px; "
                           "margin-bottom:12px; color:#0c5d23;"),
                ))
            parts.append(ui.tags.details(
                ui.tags.summary("使用した線と除外線"),
                ui.p("使用: " + ", ".join(bp.line_labels)),
                ui.p("除外 (I=0): " + (", ".join(bp.excluded) or "なし")),
                ui.p(f"R²: {bp.r_squared:.4f} / LTE 判定: {bp.lte_quality_label}"),
            ))
        return ui.div(*parts)

    # ---- Phase 5+ : Thermo DB tab ----
    @output
    @render.ui
    def thermo_output():
        if input.thermo_btn() == 0:
            return ui.p("species 名と温度を入れて「計算」を押してください。")
        name = (input.thermo_species() or "").strip()
        T = float(input.thermo_T() or 1000.0)
        e = thermo_lookup(name)
        if e is None:
            return ui.div(
                ui.tags.strong(f"⚠ '{name}' は DB に見つかりません"),
                ui.p("試した DB: gri30, nasa_gas (NASA Glenn 2002), "
                     "airNASA9, nasa_condensed", style="color:#666;"),
                style=("background:#fdeaea; border-left:3px solid #c33; "
                       "padding:10px 14px; border-radius:4px;"),
            )
        R = 8.314462618
        in_range = e.species.is_in_temperature_range(T)
        try:
            cp = e.evaluator.cp_R(T) * R
            h_RT = e.evaluator.h_RT(T)
            s_R = e.evaluator.s_R(T)
            g_RT = e.evaluator.g_RT(T)
        except ValueError:
            cp = h_RT = s_R = g_RT = float("nan")

        warn = ""
        if not in_range:
            warn = ui.div(
                f"⚠ T={T} K is outside [{e.species.Tmin}, {e.species.Tmax}] K. "
                f"値は Wilhoit 外挿の対象。",
                style=("background:#fff7e6; border-left:3px solid #c98a00; "
                       "padding:8px 12px; border-radius:4px; margin:8px 0;"),
            )
        return ui.div(
            ui.h4(f"{name}  ({e.species.formula}, M={e.species.molar_mass_g_per_mol:.2f} g/mol)"),
            warn,
            ui.tags.table(
                {"class": "table table-striped", "style": "max-width:520px"},
                ui.tags.tr(ui.tags.th("量"), ui.tags.th("値"), ui.tags.th("単位")),
                ui.tags.tr(ui.tags.td("Cp"), ui.tags.td(f"{cp:.4f}"),
                            ui.tags.td("J/mol/K")),
                ui.tags.tr(ui.tags.td("H/RT"), ui.tags.td(f"{h_RT:.4f}"),
                            ui.tags.td("dimensionless")),
                ui.tags.tr(ui.tags.td("S/R"), ui.tags.td(f"{s_R:.4f}"),
                            ui.tags.td("dimensionless")),
                ui.tags.tr(ui.tags.td("G/RT"), ui.tags.td(f"{g_RT:.4f}"),
                            ui.tags.td("dimensionless")),
                ui.tags.tr(ui.tags.td("ΔH (T)"),
                            ui.tags.td(f"{h_RT * R * T / 1000:.3f}"),
                            ui.tags.td("kJ/mol")),
                ui.tags.tr(ui.tags.td("S (T)"),
                            ui.tags.td(f"{s_R * R:.4f}"),
                            ui.tags.td("J/mol/K")),
            ),
            ui.p(f"出典: {e.species.source}", style="color:#666; font-size:0.9em;"),
            ui.p(f"温度範囲: [{e.species.Tmin}, {e.species.Tmax}] K",
                 style="color:#666; font-size:0.9em;"),
        )

    # ---- Phase 5+ : Equilibrium tab ----
    eq_state = reactive.value(None)

    @reactive.effect
    @reactive.event(input.eq_btn)
    def _eq_compute():
        names = [s.strip() for s in (input.eq_species() or "").split(",") if s.strip()]
        T = float(input.eq_T() or 2000.0)
        P = float(input.eq_P_atm() or 1.0) * 101325.0
        reactants = {}
        if float(input.eq_C() or 0) > 0:
            reactants["C"] = float(input.eq_C())
        if float(input.eq_H() or 0) > 0:
            reactants["H"] = float(input.eq_H())
        if float(input.eq_O() or 0) > 0:
            reactants["O"] = float(input.eq_O())
        try:
            if input.eq_condensed():
                cond = evaluate_condensed_insertion(names, T, P, reactants)
                eq_state.set({"type": "condensed", "result": cond})
            else:
                tp = equilibrium_tp(names, T, P, reactants)
                eq_state.set({"type": "tp", "result": tp})
            ui.notification_show("平衡計算 OK", type="message")
        except Exception as e:
            ui.notification_show(f"平衡計算エラー: {e}", type="error")
            eq_state.set(None)

    @output
    @render.ui
    def eq_output():
        st = eq_state.get()
        if st is None:
            return ui.p("左のサイドバーで計算してください。")
        if st["type"] == "condensed":
            cond = st["result"]
            r = cond.final
            ins = cond.inserted
            rej = cond.rejected[:5]
            mole_rows = sorted(r.mole_fractions.items(),
                                key=lambda kv: -kv[1])[:15]
            return ui.div(
                ui.h4(f"平衡組成 (T={r.T_K:.0f} K, P={r.P_Pa/101325:.2f} atm)"),
                ui.p(f"収束: {r.converged}, 元素保存誤差: {r.element_balance_error:.2e}, "
                     f"反復: {r.iterations}",
                     style="color:#666;"),
                ui.h5("Top 15 mole fractions"),
                ui.tags.table(
                    {"class": "table table-sm table-striped"},
                    ui.tags.tr(ui.tags.th("species"), ui.tags.th("mole fraction")),
                    *[ui.tags.tr(ui.tags.td(n), ui.tags.td(f"{x:.4e}"))
                      for n, x in mole_rows],
                ),
                (ui.div(
                    ui.tags.strong("⚠ 凝縮相が析出しました: "), ", ".join(ins),
                    ui.p(f"ΔG/RT 改善 = {cond.delta_gibbs_RT:.4g}",
                         style="color:#666; font-size:0.9em;"),
                    style=("background:#fff7e6; border-left:3px solid #c98a00; "
                           "padding:10px 14px; border-radius:4px; margin-top:10px;"),
                ) if ins else ui.div(
                    ui.tags.strong("✓ 凝縮相は析出しませんでした"),
                    ui.p(f"検査済 (rejected): {', '.join(rej) or '—'} ほか",
                         style="color:#666; font-size:0.85em;"),
                    style=("background:#e8f5ea; border-left:3px solid #1a7f37; "
                           "padding:10px 14px; border-radius:4px; margin-top:10px;"),
                )),
            )
        # type == "tp"
        r = st["result"]
        mole_rows = sorted(r.mole_fractions.items(),
                            key=lambda kv: -kv[1])[:20]
        return ui.div(
            ui.h4(f"平衡組成 (T={r.T_K:.0f} K, P={r.P_Pa/101325:.2f} atm)"),
            ui.p(f"収束: {r.converged}, 元素保存誤差: {r.element_balance_error:.2e}",
                 style="color:#666;"),
            ui.tags.table(
                {"class": "table table-sm table-striped"},
                ui.tags.tr(ui.tags.th("species"), ui.tags.th("mole fraction")),
                *[ui.tags.tr(ui.tags.td(n), ui.tags.td(f"{x:.4e}"))
                  for n, x in mole_rows],
            ),
            (ui.div(*[ui.p("⚠ " + w, style="color:#c98a00;") for w in r.warnings])
             if r.warnings else ""),
        )

    # ---- Phase 5+ : Reaction Path tab ----
    rp_state = reactive.value(None)

    @reactive.effect
    @reactive.event(input.rp_btn)
    def _rp_compute():
        names = [s.strip() for s in (input.rp_species() or "").split(",") if s.strip()]
        if not names:
            ui.notification_show("species を 1 つ以上指定してください", type="warning")
            return
        try:
            yaml_text = export_cantera_yaml(names)
            # Try to use Cantera if available
            cantera_info = None
            try:
                import cantera as ct
                sol = ct.Solution(yaml=yaml_text)
                cantera_info = (
                    f"Cantera {ct.__version__} loaded {sol.n_species} species "
                    f"with elements {list(sol.element_names)}"
                )
            except ImportError:
                cantera_info = "Cantera 未インストール (pip install cantera で有効化可能)"
            except Exception as e:
                cantera_info = f"Cantera 読込エラー: {e}"
            rp_state.set({"yaml": yaml_text, "info": cantera_info})
            ui.notification_show("Cantera YAML 生成 OK", type="message")
        except Exception as e:
            ui.notification_show(f"YAML 生成エラー: {e}", type="error")
            rp_state.set(None)

    @output
    @render.ui
    def rp_output():
        st = rp_state.get()
        if st is None:
            return ui.p("左のサイドバーで species を指定して『YAML 生成』を押してください。")
        return ui.div(
            ui.h4("Cantera YAML"),
            ui.p(st["info"], style="color:#666;"),
            ui.tags.pre(
                st["yaml"][:5000] + ("\n...（省略）..." if len(st["yaml"]) > 5000 else ""),
                style=("background:#1e1e1e; color:#e0e0e0; padding:12px; "
                       "border-radius:6px; font-family:Menlo,monospace; "
                       "font-size:0.82em; overflow-x:auto; max-height:600px;"),
            ),
        )

    # ---- Trace (all equations) tab — compact + category-grouped ----
    @output
    @render.ui
    def trace_all():
        b = bundle.get()
        all_traces = []
        if b:
            for tr in b.as_list():
                # exclude array-only quantities from Trace cards (they're better shown as plots)
                if tr.scalar() is None:
                    continue
                all_traces.append(tr)
        for tr in plasma_results.get():
            if not getattr(tr, "category", None):
                tr.category = "plasma"
            all_traces.append(tr)
        for tr in chem_results.get():
            if not getattr(tr, "category", None):
                tr.category = "chemistry"
            all_traces.append(tr)
        for tr in spec_traces.get():
            if not getattr(tr, "category", None):
                tr.category = "plasma"
            all_traces.append(tr)

        # Phase 1.2: G1-G6 ゲート評価
        gates = evaluate_gates(
            validation=validation.get(),
            bundle=b,
            spec_bp=spec_bp.get(),
        )
        gate_panel = render_gate_panel(gates)

        if not all_traces:
            return ui.div(
                gate_panel,
                ui.p("データを読み込み、各タブで計算してください。",
                     style="margin-top:14px;"),
            )
        return ui.div(
            gate_panel,
            _trace_stats_header(all_traces),
            _trace_researcher_summary(all_traces),
            _trace_controls(),
            _render_trace_categorized(all_traces),
            _TRACE_FILTER_JS,
        )

    # ---- Export ----
    @session.download(filename=lambda: safe_filename(
        current.get().label if current.get() else "report", "md"))
    def dl_md():
        b = bundle.get()
        if b is None:
            yield "# no data loaded"
            return
        all_tr = (list(b.as_list()) + list(plasma_results.get())
                  + list(chem_results.get()) + list(spec_traces.get()))
        base = build_markdown(b.waveform.label, b.waveform.meta, all_tr)
        experiment = (
            "## 実験条件レビュー\n\n"
            f"- サンプル数 N: {b.waveform.n:,}\n"
            f"- Δt: {b.waveform.dt*1e9:.4g} ns\n"
            f"- fs: {b.waveform.fs/1e6:.4g} MHz\n"
            f"- 測定窓: {b.waveform.duration*1e6:.4g} µs\n"
            f"- PRF: {float(input.prf_hz()):.6g} Hz\n\n"
        )
        kpi_lines = ["## 主要 KPI 表", "",
                     "| group | quantity | value | unit | status | source |",
                     "|---|---|---:|---|---|---|"]
        for row in paper_candidate_traces(all_tr):
            kpi_lines.append(
                f"| {row.category} | {row.name} | {display_value(row)} | "
                f"{row.unit} | {status_label(row)} | {', '.join(row.sources)} |"
            )
        kpi_block = "\n".join(kpi_lines) + "\n\n"
        yield experiment + kpi_block + anomaly_markdown(all_tr) + figure_guidance_markdown() + base

    @session.download(filename=lambda: safe_filename(
        f"{(current.get().label if current.get() else 'analysis')}_quantities", "csv"))
    def dl_csv():
        b = bundle.get()
        if b is None:
            yield "no data"
            return
        all_tr = (list(b.as_list()) + list(plasma_results.get())
                  + list(chem_results.get()) + list(spec_traces.get()))
        yield export_trace_csv(all_tr)


app = App(app_ui, server)
