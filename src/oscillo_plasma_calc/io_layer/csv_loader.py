"""CSV ↔ Waveform I/O.

Canonical on-disk schema:

    # meta: date=2026-04-23, pulse_width_us=0.281, liquid=water, gas=CO2
    time_s,voltage_V,current_A
    -2.000000e-05,-120.0,0.02
    ...

- Leading `#` comment lines carry YAML-ish key=value metadata.
- Columns are SI units only (time_s, voltage_V, current_A).
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd
import numpy as np

from .schema import Waveform


def _parse_meta(lines: list[str]) -> dict:
    meta: dict = {}
    for line in lines:
        line = line.strip()
        if not line.startswith("#"):
            continue
        body = line.lstrip("#").strip()
        if body.lower().startswith("meta:"):
            body = body[5:].strip()
        for kv in body.split(","):
            if "=" not in kv:
                continue
            k, v = kv.split("=", 1)
            k = k.strip(); v = v.strip()
            try:
                meta[k] = float(v)
            except ValueError:
                meta[k] = v
    return meta


def load_csv(csv_path: str | Path, label: str | None = None) -> Waveform:
    csv_path = Path(csv_path)
    meta_lines: list[str] = []
    with open(csv_path, "r", encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#"):
                meta_lines.append(line)
            else:
                break
    meta = _parse_meta(meta_lines)
    meta["source_file"] = str(csv_path)

    df = pd.read_csv(csv_path, comment="#")
    required = {"time_s", "voltage_V", "current_A"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")

    return Waveform(
        t=df["time_s"].to_numpy(dtype=float),
        v=df["voltage_V"].to_numpy(dtype=float),
        i=df["current_A"].to_numpy(dtype=float),
        label=label or csv_path.stem,
        meta=meta,
    )


def save_csv(wf: Waveform, csv_path: str | Path) -> Path:
    csv_path = Path(csv_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    meta_parts = [f"{k}={v}" for k, v in wf.meta.items() if k != "source_file"]
    header = "# meta: " + ", ".join(meta_parts) + "\n" if meta_parts else ""

    df = pd.DataFrame({
        "time_s": wf.t,
        "voltage_V": wf.v,
        "current_A": wf.i,
    })
    with open(csv_path, "w", encoding="utf-8") as fh:
        if header:
            fh.write(header)
        df.to_csv(fh, index=False, float_format="%.6e")
    return csv_path
