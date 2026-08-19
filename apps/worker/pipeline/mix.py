from __future__ import annotations

from pathlib import Path

import numpy as np

from pipeline.audio import load_mono, write_wav


def _loop_to(audio: np.ndarray, n: int) -> np.ndarray:
    if len(audio) >= n:
        return audio[:n]
    reps = int(np.ceil(n / max(len(audio), 1)))
    return np.tile(audio, reps)[:n]


def _pedalboard_mix(vocal: np.ndarray, bed: np.ndarray, sr: int) -> np.ndarray:
    from pedalboard import Compressor, Delay, HighpassFilter, Pedalboard, Reverb

    board = Pedalboard(
        [
            HighpassFilter(cutoff_frequency_hz=80),
            Compressor(threshold_db=-18, ratio=3.5, attack_ms=12, release_ms=80),
            Delay(delay_seconds=0.16, feedback=0.1, mix=0.1),
            Reverb(room_size=0.26, damping=0.4, wet_level=0.16, dry_level=0.88),
        ]
    )
    processed = board(vocal, sr)
    if processed.ndim > 1:
        processed = processed.mean(axis=0)
    return _balance(processed.astype(np.float32), bed)


def _balance(vocal: np.ndarray, bed: np.ndarray) -> np.ndarray:
    n = max(len(vocal), 1)
    bed = _loop_to(bed, n)
    v = vocal.astype(np.float32)
    b = bed.astype(np.float32)
    v_rms = np.sqrt(np.mean(v**2) + 1e-8)
    b_rms = np.sqrt(np.mean(b**2) + 1e-8)
    v *= 0.24 / v_rms
    b *= 0.13 / b_rms
    mixed = v + b
    peak = np.max(np.abs(mixed)) + 1e-8
    return np.clip(mixed / peak * 0.95, -1, 1)


def mix(vocal_path: Path, bed_path: Path, workdir: Path) -> Path:
    dest = workdir / "mix.wav"
    vocal, sr = load_mono(vocal_path)
    bed, _ = load_mono(bed_path, sr=sr)
    try:
        mixed = _pedalboard_mix(vocal, bed, sr)
    except Exception:
        delayed = np.pad(vocal, (int(sr * 0.08), 0))[: len(vocal)] * 0.16
        mixed = _balance(vocal + delayed, bed)
    write_wav(dest, mixed, sr)
    return dest
