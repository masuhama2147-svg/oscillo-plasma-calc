"""Pre-calculation CSV sanity check.

Produces a structured report so the UI can show a red/yellow/green banner
before any numerical analysis runs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class ValidationItem:
    level: str            # "ok" | "notice" | "warning" | "error"
    message: str
    hint: str = ""


@dataclass
class ValidationReport:
    hard_errors: list[ValidationItem] = field(default_factory=list)
    warnings:   list[ValidationItem] = field(default_factory=list)
    notices:    list[ValidationItem] = field(default_factory=list)
    ok_items:   list[ValidationItem] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return len(self.hard_errors) == 0

    def all_items(self) -> list[ValidationItem]:
        return self.hard_errors + self.warnings + self.notices + self.ok_items


REQUIRED_COLS = ("time_s", "voltage_V", "current_A")


def validate_csv(csv_path: str | Path) -> ValidationReport:
    rep = ValidationReport()
    path = Path(csv_path)
    if not path.exists():
        rep.hard_errors.append(ValidationItem(
            "error", f"ファイルが見つかりません: {path}"))
        return rep

    try:
        df = pd.read_csv(path, comment="#")
    except Exception as e:
        rep.hard_errors.append(ValidationItem(
            "error", "CSV 読み込み失敗",
            hint=f"{type(e).__name__}: {e}"))
        return rep

    cols = [c.strip() for c in df.columns]
    missing = [c for c in REQUIRED_COLS if c not in cols]
    if missing:
        rep.hard_errors.append(ValidationItem(
            "error",
            f"必須列が不足: {missing}",
            hint=(f"実際の列: {list(df.columns)}。"
                  "列名を time_s / voltage_V / current_A に揃えてください。")
        ))
        return rep

    if len(df) < 10:
        rep.hard_errors.append(ValidationItem(
            "error", f"行数が少なすぎます: {len(df)}",
            hint="最低 10 行以上のデータが必要です。"))
        return rep

    for c in REQUIRED_COLS:
        if df[c].isnull().any():
            rep.hard_errors.append(ValidationItem(
                "error", f"列 {c} に欠損値が含まれています。"))
            return rep

    rep.ok_items.append(ValidationItem("ok",
        f"列構成 OK（{len(df)} 行、列 {REQUIRED_COLS}）"))

    t = df["time_s"].to_numpy(dtype=float)
    v = df["voltage_V"].to_numpy(dtype=float)
    i = df["current_A"].to_numpy(dtype=float)

    # 1. 時間軸の単調性
    dt = np.diff(t)
    if np.any(dt <= 0):
        rep.warnings.append(ValidationItem(
            "warning", "時間軸が単調増加ではありません",
            hint="オシロの測定開始時刻を 0 秒として単調増加する並びに並べ替えてください。"))
    else:
        rep.ok_items.append(ValidationItem("ok", "時間軸は単調増加"))

    # 2. Δt のばらつき
    if dt.size > 0 and np.mean(dt) > 0:
        cv = float(np.std(dt) / np.mean(dt))
        if cv > 0.05:
            rep.warnings.append(ValidationItem(
                "warning",
                f"Δt のばらつき CV = {cv*100:.2f}%（>5% を検出）",
                hint="オシロのサンプリングが均一でない可能性。再取得または等間隔リサンプル推奨。"))
        else:
            rep.ok_items.append(ValidationItem(
                "ok", f"Δt 均一性 OK（CV = {cv*100:.3f}%、Δt ≈ {float(np.mean(dt))*1e9:.2f} ns）"))

    # 3. DC オフセット（先頭 2 % サンプルの平均）
    head_n = max(10, len(df) // 50)
    v_offset = float(np.mean(v[:head_n]))
    i_offset = float(np.mean(i[:head_n]))
    v_range = float(np.ptp(v))
    i_range = float(np.ptp(i))
    if v_range > 0 and abs(v_offset) / v_range > 0.02:
        rep.notices.append(ValidationItem(
            "notice",
            f"電圧に DC オフセット推定値 {v_offset:.2f} V "
            f"（ピーク間の {abs(v_offset)/v_range*100:.1f}%）",
            hint="解析前に中心合わせ（波形全体から冒頭平均を引く）を推奨。"))
    if i_range > 0 and abs(i_offset) / i_range > 0.02:
        rep.notices.append(ValidationItem(
            "notice",
            f"電流に DC オフセット推定値 {i_offset:.3f} A",
            hint="電流プローブのゼロ校正を確認してください。"))

    # 4. 桁オーダーの妥当性チェック
    if np.max(np.abs(v)) < 1.0:
        rep.warnings.append(ValidationItem(
            "warning", "電圧の最大値が 1 V 未満",
            hint="単位が mV 基準になっていないか確認。列は V 単位で統一してください。"))
    if np.max(np.abs(i)) < 1e-3:
        rep.warnings.append(ValidationItem(
            "warning", "電流の最大値が 1 mA 未満",
            hint="放電未点弧 or プローブ接続の確認を推奨。"))

    # 5. 全ゼロでないこと
    if np.all(v == 0):
        rep.hard_errors.append(ValidationItem(
            "error", "voltage_V が全てゼロです。"))
    if np.all(i == 0):
        rep.hard_errors.append(ValidationItem(
            "error", "current_A が全てゼロです。"))

    return rep
