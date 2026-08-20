from __future__ import annotations

from pathlib import Path

import numpy as np

from pipeline.audio import load_mono, write_wav
from pipeline.bed import STYLES


def _scale_pcs(genre: str) -> np.ndarray:
    style = STYLES.get(genre, STYLES["pop"])
    return np.array(style["scale"], dtype=np.float64)


def _nearest_hz(f0: float, pcs: np.ndarray) -> float:
    midi = 69.0 + 12.0 * np.log2(max(f0, 1e-6) / 440.0)
    pc = midi % 12.0
    diffs = np.minimum((pc - pcs) % 12.0, (pcs - pc) % 12.0)
    target_pc = float(pcs[int(np.argmin(diffs))])
    octv = np.floor(midi / 12.0)
    target_midi = octv * 12.0 + target_pc
    if target_midi - midi > 6:
        target_midi -= 12
    if midi - target_midi > 6:
        target_midi += 12
    return float(440.0 * (2 ** ((target_midi - 69.0) / 12.0)))


def _chunk_tune(path: Path, dest: Path, genre: str) -> Path:
    import librosa

    audio, sr = load_mono(path, sr=22050)
    pcs = _scale_pcs(genre)
    hop = int(sr * 0.22)
    out = np.zeros_like(audio)
    weight = np.zeros_like(audio)
    window = np.hanning(hop * 2).astype(np.float32)
    start = 0
    while start < len(audio):
        end = min(start + hop * 2, len(audio))
        grain = audio[start:end]
        w = window[: len(grain)]
        f0 = librosa.yin(
            grain,
            fmin=librosa.note_to_hz("C2"),
            fmax=librosa.note_to_hz("C6"),
            sr=sr,
            hop_length=256,
        )
        voiced = f0[f0 > 0]
        if len(voiced):
            median = float(np.median(voiced))
            target = _nearest_hz(median, pcs)
            n_steps = float(np.clip(12 * np.log2(target / median), -2.5, 2.5))
            if abs(n_steps) > 0.35:
                grain = librosa.effects.pitch_shift(grain, sr=sr, n_steps=n_steps)
                grain = grain[: end - start]
        out[start:end] += grain * w
        weight[start:end] += w
        start += hop
    tuned = out / np.maximum(weight, 1e-6)
    mix = np.clip(0.45 * tuned + 0.55 * audio, -1, 1).astype(np.float32)
    write_wav(dest, mix, sr)
    return dest


def correct_pitch(path: Path, workdir: Path, genre: str = "pop") -> Path:
    dest = workdir / "pitched.wav"
    try:
        return _chunk_tune(path, dest, genre)
    except Exception:
        pass
    audio, sr = load_mono(path)
    write_wav(dest, audio, sr)
    return dest
