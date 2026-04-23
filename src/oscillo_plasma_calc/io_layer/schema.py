"""Canonical in-memory waveform container (SI units)."""
from __future__ import annotations

from dataclasses import dataclass, field
import numpy as np


@dataclass
class Waveform:
    t: np.ndarray                    # [s]
    v: np.ndarray                    # [V]
    i: np.ndarray                    # [A]
    label: str = ""
    meta: dict = field(default_factory=dict)

    def __post_init__(self):
        self.t = np.asarray(self.t, dtype=float)
        self.v = np.asarray(self.v, dtype=float)
        self.i = np.asarray(self.i, dtype=float)
        if not (self.t.shape == self.v.shape == self.i.shape):
            raise ValueError(
                f"shape mismatch: t{self.t.shape} v{self.v.shape} i{self.i.shape}"
            )

    @property
    def dt(self) -> float:
        if self.t.size < 2:
            raise ValueError("need >=2 samples to compute dt")
        return float(np.median(np.diff(self.t)))

    @property
    def fs(self) -> float:
        return 1.0 / self.dt

    @property
    def duration(self) -> float:
        return float(self.t[-1] - self.t[0])

    @property
    def n(self) -> int:
        return int(self.t.size)

    def slice_time(self, t0: float, t1: float) -> "Waveform":
        mask = (self.t >= t0) & (self.t <= t1)
        return Waveform(self.t[mask], self.v[mask], self.i[mask],
                        label=self.label, meta=dict(self.meta))
