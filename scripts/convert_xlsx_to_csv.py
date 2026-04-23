"""Convert `オシロスコープ測定結果.xlsx` into 4 canonical CSV files.

Usage:
    .venv/bin/python scripts/convert_xlsx_to_csv.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from oscillo_plasma_calc.io_layer import load_xlsx, save_csv


def main() -> None:
    xlsx = ROOT / "オシロスコープ測定結果.xlsx"
    out_dir = ROOT / "data_csv"
    out_dir.mkdir(parents=True, exist_ok=True)

    waveforms = load_xlsx(xlsx)
    print(f"Loaded {len(waveforms)} measurement sheets from {xlsx.name}")

    for wf in waveforms:
        safe = wf.label.replace("目盛", "_").replace(".", "p")
        out = out_dir / f"{safe}.csv"
        save_csv(wf, out)
        print(f"  {wf.label}  →  {out}  (N={wf.n}, Δt={wf.dt*1e9:.2f} ns, "
              f"Vpp={wf.v.max()-wf.v.min():.2f} V, Ipp={wf.i.max()-wf.i.min():.2f} A)")


if __name__ == "__main__":
    main()
