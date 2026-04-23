"""Noise reduction for oscilloscope waveforms."""
from __future__ import annotations

import numpy as np
from scipy.signal import savgol_filter


def moving_average(x: np.ndarray, window: int = 5) -> np.ndarray:
    if window <= 1:
        return np.asarray(x, dtype=float)
    kernel = np.ones(window) / window
    return np.convolve(np.asarray(x, dtype=float), kernel, mode="same")


def savgol_smooth(x: np.ndarray, window: int = 21, poly: int = 3) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    if window % 2 == 0:
        window += 1
    window = min(window, len(x) - 1 if len(x) % 2 == 0 else len(x))
    if window <= poly:
        return x
    return savgol_filter(x, window, poly)
