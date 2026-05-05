"""Cross-platform filename sanitization for downloads.

Windows is the strictest filesystem we target:
- forbids `< > : " / \\ | ? *` and control characters 0x00-0x1F
- reserves device names CON / PRN / AUX / NUL / COM1-9 / LPT1-9 (any case, any extension)
- forbids trailing dots and spaces
- max path = 260 chars (we cap base name at 100 to stay safe)
"""
from __future__ import annotations

import re
from datetime import datetime

_BAD_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WIN_RESERVED = (
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)
_MAX_BASE = 100


def safe_filename(label: str, ext: str = "txt", with_timestamp: bool = True) -> str:
    """Return a filesystem-safe filename derived from `label`.

    >>> safe_filename("PW目盛1.50", "md")  # doctest: +SKIP
    'PW目盛1.50_20260502-120000.md'
    >>> safe_filename("a/b:c?", "csv", with_timestamp=False)
    'a_b_c_.csv'
    >>> safe_filename("CON", "md", with_timestamp=False)
    '_CON.md'
    """
    label = label or ""
    base = _BAD_CHARS.sub("_", label).strip(". ")
    if base.upper() in _WIN_RESERVED:
        base = "_" + base
    if not base:
        base = "report"
    if len(base) > _MAX_BASE:
        base = base[:_MAX_BASE]
    if with_timestamp:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        base = f"{base}_{ts}"
    return f"{base}.{ext.lstrip('.')}"
