from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from pipeline.audio import load_mono, use_gpu_models, write_wav


def _hpss_noise_reduce(audio: np.ndarray) -> np.ndarray:
    spec = np.fft.rfft(audio)
    mag = np.abs(spec)
    thresh = np.median(mag) * 1.6
    spec[mag < thresh] *= 0.15
    out = np.fft.irfft(spec, n=len(audio)).astype(np.float32)
    return np.clip(out, -1.0, 1.0)


def _vocals_from_separated(separated: object):
    if isinstance(separated, dict):
        vocals = separated.get("vocals")
        if vocals is not None:
            return vocals
        raise RuntimeError("Demucs did not return vocals")
    names = getattr(separated, "keys", None)
    if callable(names):
        mapping = {str(k): separated[k] for k in separated.keys()}  # type: ignore[index]
        if "vocals" in mapping:
            return mapping["vocals"]
    raise RuntimeError("Unexpected Demucs output")


def _demucs(path: Path, out: Path) -> Path:
    from demucs.api import Separator
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = os.environ.get("DEMUCS_MODEL", "htdemucs")
    separator = Separator(model=model, device=device)
    _origin, separated = separator.separate_audio_file(str(path))
    vocals = _vocals_from_separated(separated)
    wave = vocals.detach().cpu().numpy() if hasattr(vocals, "detach") else np.asarray(vocals)
    if wave.ndim == 2:
        wave = wave.mean(axis=0)
    elif wave.ndim > 2:
        wave = wave.mean(axis=tuple(range(wave.ndim - 1)))
    sr = int(getattr(separator, "samplerate", 44100))
    write_wav(out, np.clip(wave.astype(np.float32), -1, 1), sr)
    return out


def clean(path: Path, workdir: Path) -> Path:
    dest = workdir / "cleaned.wav"
    if use_gpu_models():
        try:
            return _demucs(path, dest)
        except Exception:
            pass
    audio, sr = load_mono(path)
    write_wav(dest, _hpss_noise_reduce(audio), sr)
    return dest
