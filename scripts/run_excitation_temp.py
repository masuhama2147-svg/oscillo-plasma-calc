"""CLI: compute excitation temperature Te from a spectroscopy CSV.

Examples
--------
  # emit a template for hydrogen lines:
  .venv/bin/python scripts/run_excitation_temp.py --template H --out data_csv/H_template.csv

  # analyze a filled-in CSV:
  .venv/bin/python scripts/run_excitation_temp.py data_csv/my_spectrum.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from oscillo_plasma_calc.spectroscopy import (
    excitation_temperature,
    load_intensity_csv,
    save_intensity_template,
    list_elements,
)
from oscillo_plasma_calc.report.markdown import save_markdown


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", nargs="?", help="spectroscopy CSV")
    ap.add_argument("--template", choices=list_elements() + [None],
                    default=None,
                    help="emit a blank intensity template for this element")
    ap.add_argument("--out", default=None, help="output path (md report or template csv)")
    args = ap.parse_args()

    if args.template:
        out = Path(args.out) if args.out else ROOT / "data_csv" / f"{args.template}_template.csv"
        save_intensity_template(args.template, out)
        print(f"template written: {out}")
        return

    if not args.input:
        ap.error("input CSV is required (or use --template EL)")

    grouped, meta = load_intensity_csv(args.input)
    print(f"meta: {meta}")
    print(f"elements detected: {list(grouped.keys())}\n")

    traces = []
    for el, intensities in grouped.items():
        res, tr = excitation_temperature(el, intensities)
        print(f"[{el}] n_used={res.n_used}, Te = {res.Te_K:.4g} K "
              f"(slope m = {res.slope:.4g}, used={res.line_labels}, "
              f"excluded={res.excluded})")
        traces.append(tr)

    out_md = Path(args.out) if args.out else ROOT / "reports" / f"{Path(args.input).stem}_Te.md"
    save_markdown(out_md, label=Path(args.input).stem, meta=meta, traces=traces)
    print(f"\nreport: {out_md}")


if __name__ == "__main__":
    main()
