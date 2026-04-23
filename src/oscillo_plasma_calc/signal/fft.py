"""Power-spectrum (rFFT) for voltage / current waveforms."""
from __future__ import annotations

import numpy as np
from scipy.fft import rfft, rfftfreq


def power_spectrum(x: np.ndarray, dt: float) -> tuple[np.ndarray, np.ndarray]:
    """Return (frequency [Hz], one-sided amplitude spectrum)."""
    x = np.asarray(x, dtype=float)
    n = x.size
    X = rfft(x * np.hanning(n))
    freq = rfftfreq(n, d=dt)
    amp = (2.0 / n) * np.abs(X)
    return freq, amp


def dominant_frequency(x: np.ndarray, dt: float) -> float:
    freq, amp = power_spectrum(x, dt)
    if freq.size < 2:
        return float("nan")
    k = int(np.argmax(amp[1:])) + 1   # skip DC
    return float(freq[k])
