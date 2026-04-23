"""xlsx / csv round-trip tests against real Nomura-lab data."""
from pathlib import Path
import numpy as np

from oscillo_plasma_calc.io_layer import load_xlsx, load_csv, save_csv

ROOT = Path(__file__).resolve().parent.parent
XLSX = ROOT / "オシロスコープ測定結果.xlsx"


def test_xlsx_load_four_sheets():
    assert XLSX.exists()
    wfs = load_xlsx(XLSX)
    assert len(wfs) == 4
    for wf in wfs:
        assert wf.v.shape == (10000,)
        assert wf.i.shape == (10000,)
        assert 1.5e-9 < wf.dt < 2.5e-9          # ≈ 2 ns
        assert wf.label.startswith("PW目盛")
        assert "pulse_width_us" in wf.meta


def test_csv_round_trip(tmp_path):
    wf = load_xlsx(XLSX, sheet_name="PW目盛0.50")[0]
    csv = tmp_path / "rt.csv"
    save_csv(wf, csv)
    wf2 = load_csv(csv)
    assert np.allclose(wf.t, wf2.t)
    assert np.allclose(wf.v, wf2.v)
    assert np.allclose(wf.i, wf2.i)
