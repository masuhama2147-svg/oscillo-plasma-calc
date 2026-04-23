"""CSV ↔ Boltzmann-plot intensity I/O.

Canonical schema (single-element):

    # meta: element=H, date=2026-04-23, sample=PW150
    line,intensity
    Halpha,16473.9
    Hbeta,5291.44
    Hgamma,1272.68

Multi-element schema (recommended for field use):

    # meta: date=2026-04-23, sample=PW150
    element,line,intensity
    H,Halpha,16473.9
    H,Hbeta,5291.44
    H,Hgamma,1272.68
    O,O1,24888.9
    O,O4,9623.82

Rules
-----
* Lines with intensity == 0 are treated as excluded (matches the xlsx).
* Unknown line labels raise a KeyError on demand via `lines.find_line`.
* Comment lines beginning with `#` may carry free key=value metadata.
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd

from .lines import LINE_DATABASE


def _parse_meta(lines: list[str]) -> dict:
    meta: dict = {}
    for line in lines:
        body = line.strip().lstrip("#").strip()
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


def load_intensity_csv(csv_path: str | Path
                       ) -> tuple[dict[str, dict[str, float]], dict]:
    """Return (per_element_intensities, metadata).

    `per_element_intensities` is a mapping element → {line_label: intensity}.
    If the CSV has only `line,intensity` columns, the element must be given in
    the `# meta: element=XX` line.
    """
    csv_path = Path(csv_path)
    meta_lines: list[str] = []
    with open(csv_path, "r", encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#"):
                meta_lines.append(line)
            else:
                break
    meta = _parse_meta(meta_lines)

    df = pd.read_csv(csv_path, comment="#")
    cols = {c.strip().lower(): c for c in df.columns}

    if "element" in cols:
        el_col = cols["element"]; line_col = cols["line"]; int_col = cols["intensity"]
        grouped: dict[str, dict[str, float]] = {}
        for _, row in df.iterrows():
            el = str(row[el_col]).strip()
            grouped.setdefault(el, {})[str(row[line_col]).strip()] = float(row[int_col])
        return grouped, meta

    if "line" in cols and "intensity" in cols:
        element = meta.get("element")
        if not element:
            raise ValueError(
                "single-element CSV requires `# meta: element=...` header line")
        line_col = cols["line"]; int_col = cols["intensity"]
        table = {str(row[line_col]).strip(): float(row[int_col])
                 for _, row in df.iterrows()}
        return {str(element): table}, meta

    raise ValueError(f"CSV must contain either "
                     f"(element,line,intensity) or (line,intensity); got {list(df.columns)}")


def save_intensity_template(element: str, csv_path: str | Path) -> Path:
    """Emit a blank CSV template pre-filled with known lines for `element`."""
    csv_path = Path(csv_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    header = (f"# meta: element={element}, date=, sample=\n"
              f"line,intensity\n")
    body = "".join(f"{ln.label},0\n" for ln in LINE_DATABASE[element])
    csv_path.write_text(header + body, encoding="utf-8")
    return csv_path
