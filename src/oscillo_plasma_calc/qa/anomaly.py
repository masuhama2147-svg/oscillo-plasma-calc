"""Post-calculation anomaly classifier ("error line").

Given a value and a key pointing to the typical-range DB, return a 4-level
classification + causes + paper references.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..docs.typical_ranges import get_range


@dataclass
class AnomalyResult:
    level: str                           # "ok" | "notice" | "warning" | "error"
    message: str                         # short 1-liner
    causes: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    range_low: float | None = None
    range_high: float | None = None
    unit: str = ""


def classify(key: str, value: float) -> AnomalyResult | None:
    """Return None when the range DB has no entry for `key`."""
    tr = get_range(key)
    if tr is None:
        return None

    low, high = tr.low, tr.high
    unit = tr.unit
    base = dict(range_low=low, range_high=high, unit=unit)
    # extreme excursions → error
    if value < low * 0.1 or value > high * 10 or value != value:  # NaN
        if value != value:
            return AnomalyResult(
                level="error",
                message="値が NaN（計算未定義）",
                causes=["入力データが不完全", "ゼロ割などの数値的不定"],
                references=list(tr.references), **base)
        if value < low:
            return AnomalyResult(
                level="error",
                message=f"値 {value:.4g} {unit} が典型下限 {low:.4g} を 1 桁以上下回ります",
                causes=list(tr.below_low_causes),
                references=list(tr.references), **base)
        return AnomalyResult(
            level="error",
            message=f"値 {value:.4g} {unit} が典型上限 {high:.4g} を 1 桁以上上回ります",
            causes=list(tr.above_high_causes),
            references=list(tr.references), **base)

    # outside [low, high] but within 10× → warning
    if value < low:
        return AnomalyResult(
            level="warning",
            message=f"典型範囲 {low:.4g}–{high:.4g} {unit} の下側。可能性のある原因を確認",
            causes=list(tr.below_low_causes),
            references=list(tr.references), **base)
    if value > high:
        return AnomalyResult(
            level="warning",
            message=f"典型範囲 {low:.4g}–{high:.4g} {unit} の上側。可能性のある原因を確認",
            causes=list(tr.above_high_causes),
            references=list(tr.references), **base)

    # near edge (within lowest 20 % or highest 20 % of log range) → notice
    try:
        import math
        log_low, log_high = math.log10(low), math.log10(high)
        pos = (math.log10(abs(value)) - log_low) / (log_high - log_low) \
              if value > 0 else 0.5
        if pos < 0.15:
            return AnomalyResult(
                level="notice",
                message=f"典型範囲内だが下限寄り（{low:.4g}–{high:.4g} {unit}）",
                causes=[], references=list(tr.references), **base)
        if pos > 0.85:
            return AnomalyResult(
                level="notice",
                message=f"典型範囲内だが上限寄り（{low:.4g}–{high:.4g} {unit}）",
                causes=[], references=list(tr.references), **base)
    except ValueError:
        pass

    return AnomalyResult(
        level="ok",
        message=f"典型範囲内（{low:.4g}–{high:.4g} {unit}）",
        causes=[], references=list(tr.references), **base)
