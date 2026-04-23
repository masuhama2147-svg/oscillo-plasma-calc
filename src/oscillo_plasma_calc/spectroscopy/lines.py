"""Atomic spectral-line database for excitation-temperature Boltzmann plots.

All constants transcribed from `励起温度計算シート ver.2.xlsx` (Nomura lab).
Each line carries its own wavelength, upper/lower level energies, statistical
weight, and Einstein A coefficient — everything required for the Boltzmann
plot method.

Per-element line sets:
  - H   : Hα, Hβ, Hγ                (lower state 2p, common)
  - O   : O1–O6 (two multiplets, lower states 3s)
  - W   : W1–W5                     (UV/visible W I lines)
  - Al  : Al1–Al5                   (mix of ground and excited lower levels)
  - Cu_i (銅①)  : Cu1-Cu5  (default-intensity set #1)
  - Cu_ii (銅②) : Cu1-Cu5  (same atomic constants, different default intensities)

"Cu_i" and "Cu_ii" reproduce the xlsx's two separate Cu worksheets that share
the same line constants but record different experimental campaigns.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class SpectralLine:
    label: str
    wavelength_nm: float   # λ [nm]
    E_upper_eV: float      # E_u  [eV]
    E_lower_eV: float      # E_l  [eV]
    g_upper: float         # statistical weight of upper level
    A_Einstein: float      # Einstein A coefficient [1/s]
    upper_config: str = ""
    lower_config: str = ""

    @property
    def dE_eV(self) -> float:
        return self.E_upper_eV - self.E_lower_eV


# ---------- 水素 H I ---------- (shared lower state 2p, E_l = 10.199 eV)
H_LINES: List[SpectralLine] = [
    SpectralLine("Halpha", 656.279, 12.0875115582, 10.1988358, 18, 4.4101e7,
                 "3s,3p,3d", "2p"),
    SpectralLine("Hbeta",  486.135, 12.7485,        10.1988358, 32, 8.4193e6,
                 "4s,4p,4d", "2p"),
    SpectralLine("Hgamma", 434.047, 13.0545,        10.1988358, 50, 2.5304e6,
                 "5s,5p,5d", "2p"),
]

# ---------- 酸素 O I ----------
O_LINES: List[SpectralLine] = [
    SpectralLine("O1", 777.539, 10.740225,   9.1460911, 3, 3.69e7,
                 "2s22p3(4S°)3p", "2s22p3(4S°)3s"),
    SpectralLine("O2", 777.417, 10.7404756,  9.1460911, 5, 3.69e7,
                 "2s22p3(4S°)3p", "2s22p3(4S°)3s"),
    SpectralLine("O3", 777.194, 10.7409314,  9.1460911, 7, 3.69e7,
                 "2s22p3(4S°)3p", "2s22p3(4S°)3s"),
    SpectralLine("O4", 844.625, 10.9888811,  9.5213638, 1, 3.22e7,
                 "2s22p3(4S°)3p", "2s22p3(4S°)3s"),
    SpectralLine("O5", 844.636, 10.9555616,  9.5213638, 5, 3.22e7,
                 "2s22p3(4S°)3p", "2s22p3(4S°)3s"),
    SpectralLine("O6", 844.676, 10.9887923,  9.5213638, 3, 3.22e7,
                 "2s22p3(4S°)3p", "2s22p3(4S°)3s"),
]

# ---------- タングステン W I ----------
W_LINES: List[SpectralLine] = [
    SpectralLine("W1", 400.875, 3.45788,   0.365913, 9,  1.63e7, "5d5(6S)6p",    "5d5(6S)6s"),
    SpectralLine("W2", 407.436, 3.408091,  0.365913, 7,  1.00e7, "5d5(6S)6p",    "5d5(6S)6s"),
    SpectralLine("W3", 429.461, 3.252077,  0.365913, 5,  1.24e7, "5d5(6S)6p",    "5d5(6S)6s"),
    SpectralLine("W4", 361.752, 3.79226,   0.365913, 7,  1.10e7, "5d46s(6D)6p",  "5d5(6S)6s"),
    SpectralLine("W5", 321.556, 4.625746,  0.771099, 11, 2.10e7, "-",             "5d46s2"),
]

# ---------- アルミニウム Al I ----------
AL_LINES: List[SpectralLine] = [
    SpectralLine("Al1", 394.4006,  3.1427212, 0.0,       2, 4.99e7, "3s24s", "3s23p"),
    SpectralLine("Al2", 396.152,   3.1427212, 0.0138938, 2, 9.85e7, "3s24s", "3s23p"),
    SpectralLine("Al3", 308.21529, 4.0214836, 0.0,       4, 5.87e7, "3s23d", "3s23p"),
    SpectralLine("Al4", 309.27099, 4.0216502, 0.0138938, 6, 7.29e7, "3s23d", "3s23p"),
    SpectralLine("Al5", 669.6015,  4.993821,  3.1427212, 4, 1.00e6, "3s25p", "3s24s"),
]

# ---------- 銅 Cu I ----------  (same constants used on 銅① and 銅② sheets)
CU_LINES: List[SpectralLine] = [
    SpectralLine("Cu1", 324.754,  3.816692,  0.0,       4, 1.395e8, "3d104p", "3d104s"),
    SpectralLine("Cu2", 327.3957, 3.7858977, 0.0,       2, 1.376e8, "3d104p", "3d104s"),
    SpectralLine("Cu3", 510.5541, 3.816692,  1.388948,  4, 2.00e6,  "3d104p", "3d94s2"),
    SpectralLine("Cu4", 515.3235, 6.1911751, 3.7858977, 4, 6.00e7,  "3d104d", "3d104p"),
    SpectralLine("Cu5", 521.8202, 6.1920252, 3.816692,  6, 7.50e7,  "3d104d", "3d104p"),
]


LINE_DATABASE: Dict[str, List[SpectralLine]] = {
    "H":  H_LINES,
    "O":  O_LINES,
    "W":  W_LINES,
    "Al": AL_LINES,
    "Cu": CU_LINES,
}


def list_elements() -> list[str]:
    return list(LINE_DATABASE.keys())


def get_lines(element: str) -> list[SpectralLine]:
    if element not in LINE_DATABASE:
        raise KeyError(f"Unknown element '{element}'. Known: {list_elements()}")
    return LINE_DATABASE[element]


def find_line(element: str, label: str) -> SpectralLine:
    for ln in get_lines(element):
        if ln.label.lower() == label.lower():
            return ln
    raise KeyError(f"No line '{label}' for element '{element}'. "
                   f"Available: {[l.label for l in get_lines(element)]}")
