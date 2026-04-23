"""Structured calculation-trace objects: equation → substitution → numeric value.

Every compute function in electrical/, plasma/, chemistry/ returns a TraceResult
so the Shiny UI can render the *full derivation* via MathJax and the PDF export
can embed the same LaTeX block.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class TraceResult:
    name: str                               # e.g. "Instantaneous power P(t)"
    value: Any                              # scalar or np.ndarray
    unit: str                               # e.g. "W"
    equation_latex: str                     # e.g. r"P(t) = V(t)\,I(t)"
    substitution_latex: str = ""            # e.g. r"P = 11840 \times 56"
    steps: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    extra: dict = field(default_factory=dict)
    # Attached by pipeline / UI for richer rendering:
    explanation_key: str | None = None       # → docs.explanations.get_explanation(key)
    anomaly: Any = None                       # qa.anomaly.AnomalyResult | None
    category: str = "electrical"              # "electrical"|"plasma"|"chemistry"|"operational"|"signal_quality"

    def scalar(self) -> float | None:
        if isinstance(self.value, (int, float, np.floating, np.integer)):
            return float(self.value)
        if isinstance(self.value, np.ndarray) and self.value.ndim == 0:
            return float(self.value)
        return None

    def summary(self) -> str:
        v = self.scalar()
        if v is not None:
            return f"{self.name}: {v:.6g} {self.unit}"
        if isinstance(self.value, np.ndarray):
            return (f"{self.name}: array shape={self.value.shape}, "
                    f"min={np.min(self.value):.4g}, max={np.max(self.value):.4g} {self.unit}")
        return f"{self.name}: {self.value} {self.unit}"

    def to_markdown(self) -> str:
        lines = [f"### {self.name}", ""]
        lines.append(f"**式**:  $${self.equation_latex}$$")
        if self.substitution_latex:
            lines.append(f"**数値代入**:  $${self.substitution_latex}$$")
        lines.append(f"**結果**:  `{self.summary()}`")
        if self.steps:
            lines.append("")
            lines.append("**中間ステップ**:")
            for s in self.steps:
                lines.append(f"- {s}")
        if self.sources:
            lines.append("")
            lines.append("**根拠論文**: " + ", ".join(self.sources))
        lines.append("")
        return "\n".join(lines)
