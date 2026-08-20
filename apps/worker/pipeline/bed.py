from __future__ import annotations

from pathlib import Path

import numpy as np

from pipeline.audio import write_wav

STYLES: dict[str, dict] = {
    "pop": {
        "bpm": 102,
        "root": 57,
        "scale": (0, 2, 3, 5, 7, 8, 10),
        "chords": (0, 8, 3, 10),
        "swing": 0.0,
        "default": ("drums", "bass", "keys", "synth"),
    },
    "trap": {
        "bpm": 140,
        "root": 53,
        "scale": (0, 2, 3, 5, 7, 8, 10),
        "chords": (0, 8, 5, 10),
        "swing": 0.06,
        "default": ("drums", "bass", "synth", "pad"),
    },
    "rock": {
        "bpm": 118,
        "root": 52,
        "scale": (0, 2, 3, 5, 7, 8, 10),
        "chords": (0, 5, 7, 0),
        "swing": 0.0,
        "default": ("drums", "bass", "guitar"),
    },
    "lofi": {
        "bpm": 84,
        "root": 60,
        "scale": (0, 2, 4, 5, 7, 9, 11),
        "chords": (0, 7, 9, 5),
        "swing": 0.12,
        "default": ("drums", "bass", "keys", "pad"),
    },
    "slow": {
        "bpm": 68,
        "root": 50,
        "scale": (0, 2, 3, 5, 7, 8, 10),
        "chords": (0, 8, 3, 10),
        "swing": 0.04,
        "default": ("pad", "keys", "strings", "bass"),
    },
}

ALLOWED = ("drums", "bass", "keys", "guitar", "pad", "synth", "strings")


def _midi_hz(midi: float) -> float:
    return float(440.0 * (2 ** ((midi - 69.0) / 12.0)))


def _exp(n: int, tau: float) -> np.ndarray:
    return np.exp(-np.arange(n) / max(tau, 1.0)).astype(np.float32)


def _place(dest: np.ndarray, src: np.ndarray, at: int, gain: float = 1.0) -> None:
    if at >= len(dest) or at < 0:
        return
    end = min(len(dest), at + len(src))
    dest[at:end] += src[: end - at] * gain


def _kick(sr: int) -> np.ndarray:
    n = int(sr * 0.28)
    t = np.arange(n) / sr
    freq = 95.0 * np.exp(-t * 16.0)
    phase = np.cumsum(freq) / sr
    return (np.sin(2 * np.pi * phase) * np.exp(-t * 10.0)).astype(np.float32)


def _snare(sr: int) -> np.ndarray:
    n = int(sr * 0.22)
    t = np.arange(n) / sr
    noise = np.diff(np.random.randn(n).astype(np.float32), prepend=0)
    tone = np.sin(2 * np.pi * 190.0 * t)
    return ((0.72 * noise + 0.28 * tone) * np.exp(-t * 16.0)).astype(np.float32)


def _hat(sr: int, open_hat: bool = False) -> np.ndarray:
    n = int(sr * (0.18 if open_hat else 0.06))
    t = np.arange(n) / sr
    x = np.diff(np.random.randn(n).astype(np.float32), prepend=0)
    return (x * np.exp(-t * (18.0 if open_hat else 42.0))).astype(np.float32)


def _tone(freq: float, n: int, sr: int, kind: str) -> np.ndarray:
    t = np.arange(n) / sr
    if kind == "sine":
        wave = np.sin(2 * np.pi * freq * t)
    elif kind == "square":
        wave = np.sign(np.sin(2 * np.pi * freq * t)) * 0.35 + np.sin(2 * np.pi * freq * t) * 0.65
    elif kind == "saw":
        wave = 2.0 * ((freq * t) % 1.0) - 1.0
    else:
        wave = np.sin(2 * np.pi * freq * t)
        wave += 0.35 * np.sin(2 * np.pi * freq * 2 * t)
        wave += 0.12 * np.sin(2 * np.pi * freq * 3 * t)
    attack = min(int(sr * 0.02), n // 8)
    env = np.ones(n, dtype=np.float32)
    if attack:
        env[:attack] = np.linspace(0, 1, attack)
        env[-attack:] *= np.linspace(1, 0, attack)
    return (wave * env).astype(np.float32)


def _pluck(freq: float, n: int, sr: int) -> np.ndarray:
    period = max(int(sr / max(freq, 40.0)), 2)
    buf = np.random.randn(period).astype(np.float32)
    out = np.empty(n, dtype=np.float32)
    idx = 0
    for i in range(n):
        out[i] = buf[idx]
        nxt = (idx + 1) % period
        buf[idx] = 0.496 * (buf[idx] + buf[nxt])
        idx = nxt
    attack = min(int(sr * 0.004), n)
    out[:attack] *= np.linspace(0, 1, attack)
    return out


def parse_instruments(raw: str | None, genre: str) -> list[str]:
    style = STYLES.get(genre, STYLES["pop"])
    parts = [p.strip().lower() for p in (raw or "").split(",") if p.strip()]
    picked = [p for p in parts if p in ALLOWED]
    return picked or list(style["default"])


def render_bed(
    genre: str,
    instruments: list[str],
    n: int,
    sr: int = 44100,
    bpm: float | None = None,
    offset: int = 0,
    ambient: bool = False,
    vocal: np.ndarray | None = None,
) -> np.ndarray:
    rng = np.random.default_rng(17)
    style = STYLES.get(genre, STYLES["pop"])
    bpm = float(bpm) if bpm and bpm >= 40 else float(style["bpm"])
    offset = max(int(offset), 0)
    root = int(style["root"])
    chords = style["chords"]
    swing = float(style["swing"])
    step = 60.0 / bpm / 4.0
    mix = np.zeros(n, dtype=np.float32)
    if not instruments:
        instruments = list(style["default"])
    want = set(instruments)
    if ambient:
        want.discard("drums")
        want.discard("synth")

    kick = _kick(sr) if "drums" in want else None
    snare = _snare(sr) if "drums" in want else None
    hat = _hat(sr) if "drums" in want else None
    open_hat = _hat(sr, True) if "drums" in want and genre == "trap" else None

    i = 0
    while True:
        t = i * step
        if swing and i % 2 == 1:
            t += step * swing
        at = int(t * sr) + offset
        if at >= n:
            break
        bar_pos = i % 16
        chord_idx = (i // 16) % len(chords)
        chord_root = root + int(chords[chord_idx])
        notes = (chord_root, chord_root + 3 if genre != "lofi" else chord_root + 4, chord_root + 7)

        if kick is not None:
            hits = {0, 8} if genre != "trap" else {0, 6, 10}
            gain = 0.55 if genre == "slow" else 0.75
            if genre == "rock" and bar_pos in {0, 4, 8, 12}:
                _place(mix, kick, at, gain)
            elif bar_pos in hits:
                _place(mix, kick, at, 0.72 if genre == "trap" else gain)

        if snare is not None and bar_pos in {4, 12}:
            _place(mix, snare, at, 0.35 if genre in {"slow", "lofi"} else 0.55)

        if hat is not None:
            if genre == "trap" or bar_pos % 2 == 0:
                _place(mix, hat, at, 0.18 if genre == "slow" else 0.28)
            if open_hat is not None and bar_pos in {7, 15}:
                _place(mix, open_hat, at, 0.22)

        beat_len = int(step * sr * (8 if genre == "slow" else 4))
        if "bass" in want and bar_pos % 4 == 0:
            bass_midi = chord_root - 12
            if genre == "trap" and bar_pos in {0, 6, 10}:
                bass_midi = chord_root - 12
            wave = _tone(_midi_hz(bass_midi), min(beat_len, n - at), sr, "square" if genre == "rock" else "sine")
            _place(mix, wave, at, 0.28)

        if "keys" in want and bar_pos == 0:
            length = int(min(n - at, step * sr * 16))
            chord = np.zeros(length, dtype=np.float32)
            for midi in notes:
                chord += _tone(_midi_hz(midi + 12), length, sr, "sine")
            attack = min(int(sr * 0.08), length)
            chord[:attack] *= np.linspace(0, 1, attack)
            _place(mix, chord / 3.0, at, 0.22 if genre == "slow" else 0.16)

        if "pad" in want and bar_pos == 0:
            length = int(min(n - at, step * sr * 16))
            pad = np.zeros(length, dtype=np.float32)
            for midi in notes:
                pad += _tone(_midi_hz(midi), length, sr, "pad")
            _place(mix, pad / 3.0, at, 0.2)

        if "strings" in want and bar_pos == 0:
            length = int(min(n - at, step * sr * 16))
            layer = np.zeros(length, dtype=np.float32)
            for midi in (notes[0] + 12, notes[2] + 12):
                layer += _tone(_midi_hz(midi), length, sr, "pad")
            _place(mix, layer / 2.0, at, 0.14)

        if "synth" in want and bar_pos % 8 == 0:
            arp = chord_root + 12 + int(style["scale"][(i // 8) % len(style["scale"])])
            wave = _tone(_midi_hz(arp), min(int(step * sr * 2), n - at), sr, "saw")
            _place(mix, wave, at, 0.1)

        if "guitar" in want and bar_pos % 2 == 0:
            midi = notes[bar_pos % 3]
            pluck = _pluck(_midi_hz(midi), min(int(step * sr * 2), n - at), sr)
            _place(mix, pluck, at, 0.16)

        i += 1

    if vocal is not None and len(vocal) == n:
        win = max(int(sr * 0.08), 64)
        env = np.convolve(np.abs(vocal.astype(np.float32)), np.ones(win) / win, mode="same")
        env /= float(np.max(env) + 1e-8)
        if ambient:
            mix *= 0.25 + 0.75 * env
        else:
            mix *= 0.55 + 0.45 * env

    if genre == "lofi":
        mix *= 0.92 + 0.08 * np.sin(2 * np.pi * np.arange(n) / sr * 0.4)
        mix += rng.normal(0, 0.003, n).astype(np.float32)

    fade = min(int(sr * 0.04), n // 10)
    if fade:
        mix[:fade] *= np.linspace(0, 1, fade)
        mix[-fade:] *= np.linspace(1, 0, fade)
    peak = float(np.max(np.abs(mix)) + 1e-8)
    return np.clip(mix / peak * 0.72, -1, 1).astype(np.float32)


def write_bed(
    dest: Path,
    genre: str,
    instruments: list[str],
    n: int,
    sr: int = 44100,
    bpm: float | None = None,
    offset: int = 0,
    ambient: bool = False,
    vocal: np.ndarray | None = None,
) -> Path:
    return write_wav(
        dest,
        render_bed(genre, instruments, n, sr, bpm=bpm, offset=offset, ambient=ambient, vocal=vocal),
        sr,
    )
