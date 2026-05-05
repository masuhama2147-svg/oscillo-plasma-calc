"""Minimal LXCat-format cross-section parser.

LXCat (https://lxcat.net) is the standard public repository of
electron-collision cross-section data for plasma physics. Each dataset
is distributed as a plain-text file with a sequence of blocks:

    PROCESS: e + N2 → e + N2 (elastic)
    SPECIES: e / N2
    PROCESS_TYPE: ELASTIC
    PARAM.:  E0 = 0.0 eV
    -----------------------------
    0.0     1.234e-20
    0.1     1.450e-20
    ...
    -----------------------------

We support the two common dialects:
- one PROCESS per block, dashes as block delimiters
- header lines beginning with `PROCESS`, `SPECIES`, `PROCESS_TYPE`,
  `THRESHOLD` (or `PARAM.: E0`)
- numeric data: two columns (energy [eV], cross-section [m²])

The parser returns a list of `CrossSection` objects with interpolators.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class CrossSection:
    process_name: str
    process_type: str            # "ELASTIC" | "EXCITATION" | "IONIZATION" | "ATTACHMENT"
    threshold_eV: float
    energies_eV: np.ndarray
    sigmas_m2: np.ndarray

    def at(self, eps_eV: float) -> float:
        """Linearly interpolate the cross-section at energy ε [eV]."""
        if eps_eV < self.threshold_eV:
            return 0.0
        if eps_eV <= self.energies_eV[0]:
            return float(self.sigmas_m2[0])
        if eps_eV >= self.energies_eV[-1]:
            return float(self.sigmas_m2[-1])
        return float(np.interp(eps_eV, self.energies_eV, self.sigmas_m2))


_HEADER_KEYS = ("PROCESS", "SPECIES", "PROCESS_TYPE", "THRESHOLD",
                 "PARAM.", "COLUMNS", "COMMENT", "UPDATED")
_NUM_RE = re.compile(r"^\s*[\d.+\-eE]+\s+[\d.+\-eE]+\s*$")


def parse_lxcat(text: str) -> list[CrossSection]:
    """Parse an LXCat-format text and return a list of CrossSections.

    Skips invalid blocks silently (returns only valid entries).
    """
    cross_sections: list[CrossSection] = []
    blocks = re.split(r"-{5,}", text)         # split on dash separators
    pending_meta: dict[str, str] = {}
    for block in blocks:
        lines = block.strip().splitlines()
        meta = dict(pending_meta)
        data_pairs: list[tuple[float, float]] = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                continue
            handled = False
            for key in _HEADER_KEYS:
                if line.startswith(key):
                    if ":" in line:
                        _, val = line.split(":", 1)
                    else:
                        val = line.split(None, 1)[1] if " " in line else ""
                    meta[key] = val.strip()
                    handled = True
                    break
            if handled:
                continue
            if _NUM_RE.match(line):
                parts = line.split()
                try:
                    data_pairs.append((float(parts[0]), float(parts[1])))
                except (ValueError, IndexError):
                    pass
        pending_meta = meta            # carry header into next block in some dialects
        if data_pairs:
            energies = np.array([p[0] for p in data_pairs])
            sigmas = np.array([p[1] for p in data_pairs])
            threshold = 0.0
            tstr = meta.get("THRESHOLD") or meta.get("PARAM.") or ""
            m = re.search(r"([\d.eE+\-]+)", tstr)
            if m:
                try:
                    threshold = float(m.group(1))
                except ValueError:
                    threshold = 0.0
            cross_sections.append(CrossSection(
                process_name=meta.get("PROCESS", "unknown"),
                process_type=meta.get("PROCESS_TYPE",
                                       _infer_type(meta.get("PROCESS", ""))),
                threshold_eV=threshold,
                energies_eV=energies,
                sigmas_m2=sigmas,
            ))
            pending_meta = {}
    return cross_sections


def _infer_type(name: str) -> str:
    n = name.upper()
    if "ELASTIC" in n or "ELAST" in n:
        return "ELASTIC"
    if "IONIZATION" in n or "IONIS" in n or "+ 2E" in n or "+E + E" in n:
        return "IONIZATION"
    if "ATTACH" in n:
        return "ATTACHMENT"
    return "EXCITATION"


def parse_lxcat_file(path) -> list[CrossSection]:
    return parse_lxcat(Path(path).read_text(encoding="utf-8"))
