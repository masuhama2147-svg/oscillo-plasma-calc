"""Render the G1-G6 research-decision gate panel as a sticky sidebar block.

Usage:
    from oscillo_plasma_calc.ui.components.gate_panel import render_gate_panel
    render_gate_panel(gates)  # gates: list[GateStatus]
"""
from __future__ import annotations

from typing import Iterable
from shiny import ui

from oscillo_plasma_calc.qa import GateStatus


_SEVERITY_COLOR = {
    "ok":          "#1a7f37",
    "provisional": "#c98a00",
    "locked":      "#9ca3af",
}


def _gate_chip(g: GateStatus) -> ui.Tag:
    color = _SEVERITY_COLOR.get(g.severity, "#666")
    detail_line = ui.div(g.detail or g.blocker,
                          style="font-size:0.78em; color:#555; margin-top:2px;")
    return ui.div(
        ui.div(
            ui.tags.span(g.icon, style="font-size:1.1em; margin-right:6px;"),
            ui.tags.strong(g.name, style=f"color:{color};"),
            style="display:flex; align-items:center;",
        ),
        detail_line,
        style=(f"border-left:3px solid {color}; padding:6px 10px; "
               f"margin:4px 0; background:white; border-radius:4px;"),
    )


def render_gate_panel(gates: Iterable[GateStatus]) -> ui.Tag:
    items = [_gate_chip(g) for g in gates]
    return ui.div(
        ui.h5("📊 研究判断ゲート",
              style="margin:0 0 8px 0; color:#2a6fb0;"),
        ui.p("各ゲートが ✅ になると下流計算が解放されます。",
             style="font-size:0.78em; color:#666; margin:0 0 8px 0;"),
        *items,
        style=("position:sticky; top:10px; padding:10px; "
               "background:#f1f5f9; border-radius:8px; "
               "border:1px solid #cfd8dc;"),
    )
