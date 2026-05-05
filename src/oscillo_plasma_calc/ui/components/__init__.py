"""Composable UI helpers used by the Shiny app.

Modules here are import-safe (no Shiny import at module level) so they
can be tested without spinning up a Shiny session.
"""
from .core import (
    KpiRow,
    PAPER_CANDIDATE_KEYS,
    PAPER_TEMPLATE,
    SCREEN_TEMPLATE,
    IMPORTANT_KEYS,
    anomaly_markdown,
    apply_research_plot_layout,
    display_value,
    export_trace_csv,
    figure_guidance_markdown,
    important_traces,
    paper_candidate_traces,
    plotly_mode_template,
    status_label,
    trace_rows,
    waveform_annotations,
)
from .safe_filename import safe_filename
from .gate_panel import render_gate_panel

__all__ = [
    "KpiRow",
    "PAPER_CANDIDATE_KEYS", "PAPER_TEMPLATE", "SCREEN_TEMPLATE", "IMPORTANT_KEYS",
    "anomaly_markdown", "apply_research_plot_layout",
    "display_value", "export_trace_csv", "figure_guidance_markdown",
    "important_traces", "paper_candidate_traces",
    "plotly_mode_template", "status_label", "trace_rows", "waveform_annotations",
    "safe_filename", "render_gate_panel",
]
