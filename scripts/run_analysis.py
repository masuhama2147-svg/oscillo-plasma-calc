"""CLI: run the full Tier-1 electrical analysis on a CSV or xlsx sheet and
produce a markdown report."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from oscillo_plasma_calc.io_layer import load_csv, load_xlsx
from oscillo_plasma_calc.pipeline import analyze_electrical
from oscillo_plasma_calc.report.markdown import save_markdown


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="CSV or xlsx path")
    ap.add_argument("--sheet", default=None, help="xlsx sheet name")
    ap.add_argument("--out", default=None, help="output markdown path")
    ap.add_argument("--prf", type=float, default=None,
                    help="pulse repetition frequency [Hz] for Lissajous")
    args = ap.parse_args()

    p = Path(args.input)
    if p.suffix.lower() in {".xlsx", ".xlsm"}:
        waveforms = load_xlsx(p, sheet_name=args.sheet)
        if not waveforms:
            raise SystemExit(f"No measurement sheets found in {p}")
        wf = waveforms[0]
    else:
        wf = load_csv(p)

    bundle = analyze_electrical(wf, pulse_rep_freq_hz=args.prf)
    for tr in bundle.as_list():
        print(tr.summary())

    out = Path(args.out) if args.out else ROOT / "reports" / f"{wf.label}.md"
    save_markdown(out, wf.label, wf.meta, bundle.as_list())
    print(f"\nReport written: {out}")


if __name__ == "__main__":
    main()
