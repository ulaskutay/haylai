from __future__ import annotations

from pathlib import Path

import numpy as np

from pipeline.audio import load_mono, write_wav


def _deess(audio: np.ndarray, sr: int, amount: float = 0.62) -> np.ndarray:
    spec = np.fft.rfft(audio)
    freqs = np.fft.rfftfreq(len(audio), 1 / sr)
    band = (freqs > 5500) & (freqs < 9000)
    spec[band] *= amount
    out = np.fft.irfft(spec, n=len(audio)).astype(np.float32)
    return np.clip(out, -1, 1)


def _presence(audio: np.ndarray, sr: int, genre: str) -> np.ndarray:
    spec = np.fft.rfft(audio)
    freqs = np.fft.rfftfreq(len(audio), 1 / sr)
    spec[freqs < 70] *= 0.45
    if genre in {"pop", "trap"}:
        spec[(freqs > 2800) & (freqs < 5200)] *= 1.06
        spec[freqs > 6500] *= 0.88
    else:
        spec[(freqs > 80) & (freqs < 180)] *= 0.85
        spec[(freqs > 2500) & (freqs < 5000)] *= 1.12
    out = np.fft.irfft(spec, n=len(audio)).astype(np.float32)
    return np.clip(out, -1, 1)


def enhance(path: Path, workdir: Path, genre: str = "pop", rvc_applied: bool = False) -> Path:
    """Single vocal polish pass — avoid stacking heavy FX again in mix."""
    dest = workdir / "enhanced.wav"
    audio, sr = load_mono(path)
    dry = genre in {"pop", "trap"}
    try:
        from pedalboard import Compressor, HighpassFilter, Limiter, Pedalboard

        if dry:
            board = Pedalboard(
                [
                    HighpassFilter(cutoff_frequency_hz=75),
                    Compressor(threshold_db=-22, ratio=2.0, attack_ms=10, release_ms=110),
                    Limiter(threshold_db=-2.0, release_ms=80),
                ]
            )
        else:
            from pedalboard import LowShelfFilter

            board = Pedalboard(
                [
                    HighpassFilter(cutoff_frequency_hz=85),
                    LowShelfFilter(cutoff_frequency_hz=220, gain_db=-1.5),
                    Compressor(threshold_db=-20, ratio=2.8, attack_ms=8, release_ms=90),
                    Limiter(threshold_db=-1.4, release_ms=90),
                ]
            )
        processed = board(audio, sr)
        if processed.ndim > 1:
            processed = processed.mean(axis=0)
        audio = processed.astype(np.float32)
    except Exception:
        pass

    deess_amount = 0.72 if rvc_applied else 0.68 if dry else 0.62
    audio = _deess(audio, sr, amount=deess_amount)
    audio = _presence(audio, sr, genre)
    if not dry:
        audio = np.tanh(audio * 1.12).astype(np.float32)

    peak = float(np.max(np.abs(audio)) + 1e-8)
    target = 0.78 if dry else 0.92
    write_wav(dest, np.clip(audio / peak * target, -1, 1), sr)
    return dest
