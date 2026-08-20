from __future__ import annotations

from pathlib import Path

import numpy as np

from pipeline.audio import load_mono, use_gpu_models, write_wav


def _hpss_noise_reduce(audio: np.ndarray) -> np.ndarray:
    spec = np.fft.rfft(audio)
    mag = np.abs(spec)
    thresh = np.median(mag) * 1.35
    spec[mag < thresh] *= 0.08
    out = np.fft.irfft(spec, n=len(audio)).astype(np.float32)
    return np.clip(out, -1.0, 1.0)


def _highpass(audio: np.ndarray, sr: int, cutoff: float = 80.0) -> np.ndarray:
    spec = np.fft.rfft(audio)
    freqs = np.fft.rfftfreq(len(audio), 1 / sr)
    spec[freqs < cutoff] *= 0.08
    return np.fft.irfft(spec, n=len(audio)).astype(np.float32)


def _gate(audio: np.ndarray, sr: int) -> np.ndarray:
    win = max(int(sr * 0.02), 64)
    envelope = np.sqrt(np.convolve(audio**2, np.ones(win) / win, mode="same") + 1e-9)
    floor = float(np.percentile(envelope[: min(len(envelope), sr // 2)], 20))
    thresh = max(floor * 3.5, 0.004)
    gain = np.clip((envelope - thresh) / (thresh + 1e-6), 0.08, 1.0)
    return (audio * gain).astype(np.float32)


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
    separator = Separator(model="htdemucs", device=device)
    _origin, separated = separator.separate_audio_file(str(path))
    vocals = _vocals_from_separated(separated)
    wave = vocals.detach().cpu().numpy() if hasattr(vocals, "detach") else np.asarray(vocals)
    if wave.ndim == 2:
        wave = wave.mean(axis=0)
    elif wave.ndim > 2:
        wave = wave.mean(axis=tuple(range(wave.ndim - 1)))
    sr = int(getattr(separator, "samplerate", 44100))
    wave = _gate(_highpass(_hpss_noise_reduce(wave.astype(np.float32)), sr), sr)
    write_wav(out, np.clip(wave, -1, 1), sr)
    return out


def clean(path: Path, workdir: Path) -> Path:
    dest = workdir / "cleaned.wav"
    audio, sr = load_mono(path)
    # Short phone takes lose more than they gain from stem separation.
    if use_gpu_models() and len(audio) >= sr * 15:
        try:
            return _demucs(path, dest)
        except Exception:
            pass
    write_wav(dest, _gate(_highpass(_hpss_noise_reduce(audio), sr), sr), sr)
    return dest
