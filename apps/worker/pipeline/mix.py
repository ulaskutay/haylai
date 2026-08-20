from __future__ import annotations

from pathlib import Path

import numpy as np

from pipeline.audio import load_mono, write_wav


def _loop_to(audio: np.ndarray, n: int) -> np.ndarray:
    if len(audio) >= n:
        return audio[:n]
    reps = int(np.ceil(n / max(len(audio), 1)))
    return np.tile(audio, reps)[:n]


def _duck(vocal: np.ndarray, bed: np.ndarray, sr: int) -> np.ndarray:
    win = max(int(sr * 0.04), 32)
    env = np.sqrt(np.convolve(vocal**2, np.ones(win) / win, mode="same") + 1e-9)
    ref = float(np.percentile(env, 88) + 1e-6)
    amount = np.clip(env / ref, 0.0, 1.0)
    return bed * (1.0 - 0.32 * amount)


def _genre_board(genre: str):
    from pedalboard import Compressor, Delay, HighpassFilter, Limiter, Pedalboard, Reverb

    wet = {"slow": 0.22, "lofi": 0.16, "pop": 0.08, "trap": 0.1, "rock": 0.08}.get(genre, 0.1)
    room = {"slow": 0.38, "lofi": 0.26, "rock": 0.16}.get(genre, 0.2)
    return Pedalboard(
        [
            HighpassFilter(cutoff_frequency_hz=80),
            Compressor(threshold_db=-18, ratio=2.6, attack_ms=12, release_ms=100),
            Delay(delay_seconds=0.12 if genre != "slow" else 0.18, feedback=0.06, mix=0.04),
            Reverb(room_size=room, damping=0.5, wet_level=wet, dry_level=0.94),
            Limiter(threshold_db=-1.4, release_ms=90),
        ]
    )


def _balance(vocal: np.ndarray, bed: np.ndarray, sr: int) -> np.ndarray:
    n = max(len(vocal), 1)
    bed = _loop_to(bed, n)
    vocal = vocal.astype(np.float32)
    bed = _duck(vocal, bed.astype(np.float32), sr)
    v_rms = np.sqrt(np.mean(vocal**2) + 1e-8)
    b_rms = np.sqrt(np.mean(bed**2) + 1e-8)
    vocal *= 0.34 / v_rms
    bed *= 0.065 / b_rms
    mixed = vocal + bed
    peak = np.max(np.abs(mixed)) + 1e-8
    return np.clip(mixed / peak * 0.95, -1, 1)


def mix(vocal_path: Path, bed_path: Path, workdir: Path, genre: str = "pop") -> Path:
    dest = workdir / "mix.wav"
    vocal, sr = load_mono(vocal_path)
    bed, _ = load_mono(bed_path, sr=sr)
    try:
        processed = _genre_board(genre)(vocal, sr)
        if processed.ndim > 1:
            processed = processed.mean(axis=0)
        mixed = _balance(processed.astype(np.float32), bed, sr)
    except Exception:
        delayed = np.pad(vocal, (int(sr * 0.08), 0))[: len(vocal)] * 0.12
        mixed = _balance(vocal + delayed, bed, sr)
    write_wav(dest, mixed, sr)
    return dest
