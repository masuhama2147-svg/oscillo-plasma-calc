import numpy as np

from oscillo_plasma_calc.report.trace import TraceResult
from oscillo_plasma_calc.ui.components import (
    display_value,
    export_trace_csv,
    important_traces,
    paper_candidate_traces,
    status_label,
    waveform_annotations,
)


class DummyAnomaly:
    def __init__(self, level="ok"):
        self.level = level
        self.message = "message"


def _tr(name, value, key, category="electrical", level=None):
    tr = TraceResult(
        name=name,
        value=value,
        unit="W",
        equation_latex="x=1",
        sources=["source"],
        explanation_key=key,
        category=category,
    )
    if level:
        tr.anomaly = DummyAnomaly(level)
    return tr


def test_display_value_scientific_and_nan():
    assert display_value(_tr("a", 0.00123, "mean_power")) == "0.00123"
    assert display_value(_tr("a", 123456.0, "mean_power")) == "1.235e5"
    assert display_value(_tr("a", float("nan"), "mean_power")) == "nan"


def test_status_label_and_export_trace_csv():
    traces = [
        _tr("Peak-to-peak voltage Vpp", 6800.0, "vpp", level="ok"),
        _tr("Instantaneous power P(t)", np.array([1, 2]), "instant_power"),
    ]
    assert status_label(traces[0]) == "ok"
    csv_text = export_trace_csv(traces)
    assert "quantity,value,unit,status,source,equation_key" in csv_text
    assert "Peak-to-peak voltage Vpp,6800,W,ok,source,vpp" in csv_text
    assert "Instantaneous power" not in csv_text


def test_trace_selection_helpers_prioritize_research_kpis():
    traces = [
        _tr("Minor", 1.0, "minor"),
        _tr("G value", 2.0, "g_value", category="chemistry"),
        _tr("Rise time", 3.0, "rise_time", level="warning"),
    ]
    important = important_traces(traces)
    assert [tr.explanation_key for tr in important][:2] == ["rise_time", "g_value"]
    paper = paper_candidate_traces(traces)
    assert [tr.explanation_key for tr in paper] == ["g_value"]


def test_waveform_annotations_extract_key_points():
    t = np.linspace(0, 1e-6, 101)
    v = np.linspace(-10, 10, 101)
    i = np.sin(np.linspace(0, np.pi, 101))
    ann = waveform_annotations(t, v, i)
    assert ann["vmax"] == 10
    assert ann["vmin"] == -10
    assert 0 <= ann["t10_us"] <= ann["t90_us"] <= 1.0
    assert 0 <= ann["t_zero_us"] <= 1.0
