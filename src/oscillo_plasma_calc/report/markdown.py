"""Markdown report export for a list of TraceResult objects."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from .trace import TraceResult


HEADER = """# 液中プラズマ オシロスコープ波形 解析レポート

生成日時: {now}
データセット: {label}

{metadata_block}

---
"""


def build_markdown(label: str, meta: dict,
                   traces: list[TraceResult]) -> str:
    meta_lines = "\n".join(f"- **{k}**: {v}" for k, v in meta.items()) or "- (なし)"
    body = HEADER.format(
        now=datetime.now().isoformat(timespec="seconds"),
        label=label,
        metadata_block="## 測定メタデータ\n" + meta_lines,
    )
    for tr in traces:
        body += tr.to_markdown() + "\n"
    return body


def save_markdown(path: str | Path, label: str, meta: dict,
                  traces: list[TraceResult]) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(build_markdown(label, meta, traces), encoding="utf-8")
    return p
