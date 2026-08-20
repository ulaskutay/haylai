from __future__ import annotations

from pathlib import Path

import numpy as np

from pipeline.audio import load_mono, use_gpu_models, write_wav

_DEMUCS_MIN_SECONDS_GPU = 8.0
_DEMUCS_MIN_SECONDS_CPU = 15.0


def _hpss_noise_reduce(audio: np.ndarray, strength: float = 1.0) -> np.ndarray:
    spec = np.fft.rfft(audio)
    mag = np.abs(spec)
    mult = 1.25 + 0.25 * strength
    atten = max(0.08, 0.18 - 0.06 * strength)
    thresh = np.median(mag) * mult
    spec[mag < thresh] *= atten
    out = np.fft.irfft(spec, n=len(audio)).astype(np.float32)
    return np.clip(out, -1.0, 1.0)


def _highpass(audio: np.ndarray, sr: int, cutoff: float = 85.0) -> np.ndarray:
    spec = np.fft.rfft(audio)
    freqs = np.fft.rfftfreq(len(audio), 1 / sr)
    spec[freqs < cutoff] *= 0.05
    return np.fft.irfft(spec, n=len(audio)).astype(np.float32)


def _de_rumble(audio: np.ndarray, sr: int) -> np.ndarray:
    spec = np.fft.rfft(audio)
    freqs = np.fft.rfftfreq(len(audio), 1 / sr)
    spec[(freqs >= 85) & (freqs < 220)] *= 0.82
    return np.fft.irfft(spec, n=len(audio)).astype(np.float32)


def _gate(audio: np.ndarray, sr: int, strength: float = 1.0) -> np.ndarray:
    win = max(int(sr * 0.02), 64)
    envelope = np.sqrt(np.convolve(audio**2, np.ones(win) / win, mode="same") + 1e-9)
    floor = float(np.percentile(envelope[: min(len(envelope), sr // 2)], 18))
    thresh = max(floor * (3.0 + 0.5 * strength), 0.003)
    floor_gain = max(0.06, 0.14 - 0.04 * strength)
    gain = np.clip((envelope - thresh) / (thresh + 1e-6), floor_gain, 1.0)
    return (audio * gain).astype(np.float32)


def _level_speech(audio: np.ndarray, target_rms: float = 0.085) -> np.ndarray:
    rms = float(np.sqrt(np.mean(audio**2)) + 1e-8)
    if rms < 1e-5:
        return audio
    scaled = audio.astype(np.float32) * (target_rms / rms)
    peak = float(np.max(np.abs(scaled)) + 1e-8)
    if peak > 0.98:
        scaled = scaled / peak * 0.98
    return scaled.astype(np.float32)


def _repair_phone_vocal(audio: np.ndarray, sr: int, strength: float = 1.0) -> np.ndarray:
    x = _hpss_noise_reduce(audio, strength)
    x = _highpass(x, sr)
    x = _de_rumble(x, sr)
    x = _hpss_noise_reduce(x, strength * 0.6)
    x = _gate(x, sr, strength)
    return _level_speech(x)


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
    wave = _repair_phone_vocal(wave.astype(np.float32), sr, strength=0.85)
    write_wav(out, np.clip(wave, -1, 1), sr)
    return out


def _demucs_min_seconds() -> float:
    return _DEMUCS_MIN_SECONDS_GPU if use_gpu_models() else _DEMUCS_MIN_SECONDS_CPU


def clean(path: Path, workdir: Path) -> Path:
    dest = workdir / "cleaned.wav"
    audio, sr = load_mono(path)
    min_sec = _demucs_min_seconds()
    if use_gpu_models() and len(audio) >= sr * min_sec:
        try:
            return _demucs(path, dest)
        except Exception:
            pass
    strength = 1.15 if use_gpu_models() else 1.0
    write_wav(dest, _repair_phone_vocal(audio, sr, strength), sr)
    return dest
