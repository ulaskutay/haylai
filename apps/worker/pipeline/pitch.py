from __future__ import annotations

from pathlib import Path

import numpy as np

from pipeline.audio import load_mono, write_wav


def _quantize_hz(f0: np.ndarray) -> np.ndarray:
    out = f0.copy()
    voiced = f0 > 0
    midi = 69 + 12 * np.log2(np.clip(f0[voiced], 1e-6, None) / 440.0)
    midi = np.round(midi)
    out[voiced] = 440.0 * (2 ** ((midi - 69) / 12.0))
    return out


def _pyworld(path: Path, dest: Path) -> Path:
    import pyworld as pw

    audio, sr = load_mono(path)
    x = audio.astype(np.float64)
    f0, t = pw.harvest(x, sr)
    sp = pw.cheaptrick(x, f0, t, sr)
    ap = pw.d4c(x, f0, t, sr)
    y = pw.synthesize(_quantize_hz(f0), sp, ap, sr)
    write_wav(dest, y.astype(np.float32), sr)
    return dest


def _librosa_tune(path: Path, dest: Path) -> Path:
    import librosa

    audio, sr = load_mono(path, sr=22050)
    f0 = librosa.yin(
        audio,
        fmin=librosa.note_to_hz("C2"),
        fmax=librosa.note_to_hz("C6"),
        sr=sr,
        hop_length=512,
    )
    median = float(np.median(f0[f0 > 0])) if np.any(f0 > 0) else 0.0
    if not np.isfinite(median) or median <= 0:
        write_wav(dest, audio, sr)
        return dest
    midi = 69 + 12 * np.log2(median / 440.0)
    target = 440.0 * (2 ** ((round(midi) - 69) / 12.0))
    n_steps = 12 * np.log2(target / median)
    n_steps = float(np.clip(n_steps, -4.0, 4.0))
    tuned = librosa.effects.pitch_shift(audio, sr=sr, n_steps=n_steps)
    write_wav(dest, np.clip(tuned, -1, 1).astype(np.float32), sr)
    return dest


def correct_pitch(path: Path, workdir: Path) -> Path:
    dest = workdir / "pitched.wav"
    try:
        return _pyworld(path, dest)
    except Exception:
        pass
    try:
        return _librosa_tune(path, dest)
    except Exception:
        pass
    audio, sr = load_mono(path)
    write_wav(dest, audio, sr)
    return dest
