"""Waveform preprocessing — addresses the offset / sync issues raised at the
2026-04-23 lab meeting:

- DC offset removal (center by the baseline before the first pulse)
- Zero-crossing synchronization (align the first V rising edge to t=0)

These are opt-in helpers so the analyst can reproduce the raw-data pipeline
or a cleaned pipeline at will.
"""
from __future__ import annotations

import numpy as np

from ..io_layer.schema import Waveform


def remove_dc_offset(wf: Waveform, head_fraction: float = 0.02) -> Waveform:
    """Subtract the mean of the leading `head_fraction` samples from V and I.

    Recommended before Vpp / Ipp / RMS when the scope baseline is visibly non-zero.
    """
    n = max(10, int(round(wf.n * head_fraction)))
    v_off = float(np.mean(wf.v[:n]))
    i_off = float(np.mean(wf.i[:n]))
    meta = dict(wf.meta)
    meta["preprocessing"] = meta.get("preprocessing", "") + \
                            f" dc_offset(v={v_off:.3g},i={i_off:.3g});"
    return Waveform(
        t=wf.t.copy(),
        v=wf.v - v_off,
        i=wf.i - i_off,
        label=wf.label + " [centered]",
        meta=meta,
    )


def align_to_first_rising_edge(wf: Waveform,
                               channel: str = "V",
                               threshold_fraction: float = 0.1) -> Waveform:
    """Shift the time axis so that the first V (or I) rising edge is at t=0.

    `threshold_fraction` = 0.1 means t=0 when V reaches 10 % of its peak.
    """
    x = wf.v if channel.upper().startswith("V") else wf.i
    peak = float(np.max(np.abs(x)))
    if peak <= 0:
        return wf
    thresh = threshold_fraction * peak
    idx = int(np.argmax(np.abs(x) >= thresh))
    t0 = float(wf.t[idx])
    meta = dict(wf.meta)
    meta["preprocessing"] = meta.get("preprocessing", "") + \
                            f" aligned@{channel}{int(threshold_fraction*100)}%;"
    return Waveform(
        t=wf.t - t0,
        v=wf.v.copy(),
        i=wf.i.copy(),
        label=wf.label + " [aligned]",
        meta=meta,
    )


def preprocess(wf: Waveform,
               remove_offset: bool = True,
               align_edge: bool = False) -> Waveform:
    """Composite helper applying the two standard cleanup steps."""
    out = wf
    if remove_offset:
        out = remove_dc_offset(out)
    if align_edge:
        out = align_to_first_rising_edge(out)
    return out
