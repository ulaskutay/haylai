from __future__ import annotations

from pathlib import Path

import numpy as np

from pipeline.audio import load_mono, write_wav


def _deess(audio: np.ndarray, sr: int) -> np.ndarray:
    spec = np.fft.rfft(audio)
    freqs = np.fft.rfftfreq(len(audio), 1 / sr)
    band = (freqs > 5500) & (freqs < 9000)
    spec[band] *= 0.62
    out = np.fft.irfft(spec, n=len(audio)).astype(np.float32)
    return np.clip(out, -1, 1)


def _presence(audio: np.ndarray, sr: int) -> np.ndarray:
    spec = np.fft.rfft(audio)
    freqs = np.fft.rfftfreq(len(audio), 1 / sr)
    spec[(freqs > 80) & (freqs < 180)] *= 0.85
    spec[(freqs > 2500) & (freqs < 5000)] *= 1.12
    spec[freqs < 70] *= 0.35
    out = np.fft.irfft(spec, n=len(audio)).astype(np.float32)
    return np.clip(out, -1, 1)


def _soft_clip(audio: np.ndarray) -> np.ndarray:
    return np.tanh(audio * 1.15).astype(np.float32)


def enhance(path: Path, workdir: Path) -> Path:
    dest = workdir / "enhanced.wav"
    audio, sr = load_mono(path)
    try:
        from pedalboard import Compressor, HighpassFilter, LowShelfFilter, Pedalboard

        board = Pedalboard(
            [
                HighpassFilter(cutoff_frequency_hz=85),
                LowShelfFilter(cutoff_frequency_hz=220, gain_db=-1.5),
                Compressor(threshold_db=-20, ratio=2.8, attack_ms=8, release_ms=90),
            ]
        )
        processed = board(audio, sr)
        if processed.ndim > 1:
            processed = processed.mean(axis=0)
        audio = processed.astype(np.float32)
    except Exception:
        pass
    audio = _deess(audio, sr)
    audio = _presence(audio, sr)
    audio = _soft_clip(audio)
    peak = float(np.max(np.abs(audio)) + 1e-8)
    write_wav(dest, np.clip(audio / peak * 0.92, -1, 1), sr)
    return dest
