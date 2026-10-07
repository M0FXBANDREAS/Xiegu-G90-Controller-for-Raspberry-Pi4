"""Stereo I/Q FFT, expressed as relative dBFS, not calibrated RF power."""
import numpy as np


def spectrum(samples, swap=False):
    if samples.shape != (2048, 2):
        raise ValueError('I/Q requires exactly 2048 frames of stereo input')
    z = (samples[:, 1] + 1j * samples[:, 0]) if swap else (samples[:, 0] + 1j * samples[:, 1])
    z = z - np.mean(z)
    window = np.hanning(2048)
    fft = np.fft.fftshift(np.fft.fft(z * window))
    db = 20 * np.log10(np.maximum(np.abs(fft) / window.sum(), 1e-7))
    return db.reshape(512, 4).max(axis=1).round(1).tolist()
