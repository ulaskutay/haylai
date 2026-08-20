from __future__ import annotations

from pathlib import Path

import numpy as np

from pipeline.audio import write_wav

STYLES: dict[str, dict] = {
    "pop": {
        "bpm": 92,
        "root": 57,
        "scale": (0, 2, 3, 5, 7, 8, 10),
        "chords": (0, 8, 3, 10),
        "swing": 0.0,
        "profile": "urban",
        "default": ("drums", "bass", "keys", "pad", "perc"),
    },
    "trap": {
        "bpm": 140,
        "root": 53,
        "scale": (0, 2, 3, 5, 7, 8, 10),
        "chords": (0, 8, 5, 10),
        "swing": 0.06,
        "default": ("drums", "bass", "synth", "pad", "perc"),
    },
    "rock": {
        "bpm": 118,
        "root": 52,
        "scale": (0, 2, 3, 5, 7, 8, 10),
        "chords": (0, 5, 7, 0),
        "swing": 0.0,
        "default": ("drums", "bass", "guitar", "keys"),
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
        "default": ("drums", "bass", "pad", "keys", "strings"),
    },
}

ALLOWED = ("drums", "bass", "keys", "guitar", "pad", "synth", "strings", "perc", "brass")
BEAT_GENRES = frozenset({"pop", "trap", "rock"})

# Keep in sync with apps/web/src/lib/arrangement.ts GROOVES
GROOVES: dict[str, dict] = {
    "pop-four": {
        "genre": "pop",
        "bpm": 92,
        "kick": (0, 8),
        "snare": (4, 12),
        "hat": "8th",
        "open_hat": (),
        "clap": True,
        "tom": (),
        "swing": 0.0,
    },
    "pop-sync": {
        "genre": "pop",
        "bpm": 96,
        "kick": (0, 3, 8, 10),
        "snare": (4, 12),
        "hat": "8th",
        "open_hat": (7, 15),
        "clap": True,
        "tom": (),
        "swing": 0.04,
    },
    "pop-clap": {
        "genre": "pop",
        "bpm": 90,
        "kick": (0, 8, 11),
        "snare": (4, 12),
        "hat": "quarter",
        "open_hat": (6, 14),
        "clap": True,
        "tom": (),
        "swing": 0.0,
    },
    "trap-roll": {
        "genre": "trap",
        "bpm": 140,
        "kick": (0, 6, 10),
        "snare": (4, 12),
        "hat": "16th",
        "open_hat": (7, 15),
        "clap": True,
        "tom": (),
        "swing": 0.06,
    },
    "trap-drill": {
        "genre": "trap",
        "bpm": 144,
        "kick": (0, 7, 11),
        "snare": (4, 12),
        "hat": "16th",
        "open_hat": (5, 13),
        "clap": True,
        "tom": (),
        "swing": 0.08,
    },
    "trap-bounce": {
        "genre": "trap",
        "bpm": 136,
        "kick": (0, 4, 7, 11),
        "snare": (4, 12),
        "hat": "8th",
        "open_hat": (7, 15),
        "clap": True,
        "tom": (),
        "swing": 0.04,
    },
    "rock-four": {
        "genre": "rock",
        "bpm": 118,
        "kick": (0, 4, 8, 12),
        "snare": (4, 12),
        "hat": "8th",
        "open_hat": (),
        "clap": False,
        "tom": (),
        "swing": 0.0,
    },
    "rock-drive": {
        "genre": "rock",
        "bpm": 124,
        "kick": (0, 4, 8, 12),
        "snare": (4, 12),
        "hat": "8th",
        "open_hat": (7, 15),
        "clap": False,
        "tom": (2, 6, 10, 14),
        "swing": 0.0,
    },
    "rock-half": {
        "genre": "rock",
        "bpm": 112,
        "kick": (0, 8),
        "snare": (8,),
        "hat": "8th",
        "open_hat": (),
        "clap": False,
        "tom": (12, 14),
        "swing": 0.0,
    },
    "lofi-boom": {
        "genre": "lofi",
        "bpm": 84,
        "kick": (0, 10),
        "snare": (4, 12),
        "hat": "offbeat",
        "open_hat": (7,),
        "clap": False,
        "tom": (),
        "swing": 0.14,
    },
    "lofi-dust": {
        "genre": "lofi",
        "bpm": 78,
        "kick": (0, 8),
        "snare": (4, 12),
        "hat": "8th",
        "open_hat": (),
        "clap": False,
        "tom": (),
        "swing": 0.12,
    },
    "lofi-soft": {
        "genre": "lofi",
        "bpm": 72,
        "kick": (0,),
        "snare": (8,),
        "hat": "quarter",
        "open_hat": (),
        "clap": False,
        "tom": (),
        "swing": 0.1,
    },
    "slow-pulse": {
        "genre": "slow",
        "bpm": 68,
        "kick": (0, 8),
        "snare": (4, 12),
        "hat": "quarter",
        "open_hat": (),
        "clap": False,
        "tom": (),
        "swing": 0.04,
    },
    "slow-side": {
        "genre": "slow",
        "bpm": 62,
        "kick": (0,),
        "snare": (8,),
        "hat": "quarter",
        "open_hat": (14,),
        "clap": False,
        "tom": (),
        "swing": 0.06,
    },
    "slow-heart": {
        "genre": "slow",
        "bpm": 72,
        "kick": (0, 6, 8, 14),
        "snare": (8,),
        "hat": "8th",
        "open_hat": (),
        "clap": True,
        "tom": (),
        "swing": 0.05,
    },
}

DEFAULT_GROOVE = {
    "pop": "pop-four",
    "trap": "trap-roll",
    "rock": "rock-four",
    "lofi": "lofi-boom",
    "slow": "slow-pulse",
}


def resolve_groove(genre: str, groove_id: str | None = None) -> dict:
    style_id = genre if genre in STYLES else "pop"
    picked = GROOVES.get((groove_id or "").strip())
    if picked and picked["genre"] == style_id:
        return picked
    return GROOVES[DEFAULT_GROOVE.get(style_id, "pop-four")]


def _hat_hit(mode: str, bar_pos: int) -> bool:
    if mode == "16th":
        return True
    if mode == "8th":
        return bar_pos % 2 == 0
    if mode == "offbeat":
        return bar_pos % 2 == 1
    return bar_pos % 4 == 0


def _midi_hz(midi: float) -> float:
    return float(440.0 * (2 ** ((midi - 69.0) / 12.0)))


def _place(dest: np.ndarray, src: np.ndarray, at: int, gain: float = 1.0) -> None:
    if at >= len(dest) or at < 0:
        return
    end = min(len(dest), at + len(src))
    dest[at:end] += src[: end - at] * gain


def _env(n: int, sr: int, attack: float = 0.01, release: float = 0.08) -> np.ndarray:
    a = min(int(sr * attack), max(n // 8, 1))
    r = min(int(sr * release), max(n // 4, 1))
    out = np.ones(n, dtype=np.float32)
    if a:
        out[:a] = np.linspace(0, 1, a)
    if r:
        out[-r:] *= np.linspace(1, 0, r)
    return out


def _sub808(sr: int, midi: float = 36) -> np.ndarray:
    n = int(sr * 0.62)
    t = np.arange(n) / sr
    freq = _midi_hz(midi)
    body = np.sin(2 * np.pi * freq * t) * np.exp(-t * 2.4)
    sub = np.sin(2 * np.pi * freq * 0.5 * t) * np.exp(-t * 1.8) * 0.35
    return ((body + sub) * _env(n, sr, 0.001, 0.5)).astype(np.float32)


def _clap(sr: int) -> np.ndarray:
    n = int(sr * 0.12)
    t = np.arange(n) / sr
    noise = np.diff(np.random.randn(n).astype(np.float32), prepend=0)
    return (noise * np.exp(-t * 22.0) * _env(n, sr, 0.001, 0.06)).astype(np.float32)


def _kick(sr: int) -> np.ndarray:
    n = int(sr * 0.24)
    t = np.arange(n) / sr
    freq = 115.0 * np.exp(-t * 20.0)
    phase = np.cumsum(freq) / sr
    body = np.sin(2 * np.pi * phase) * np.exp(-t * 11.0)
    click = np.diff(np.random.randn(n).astype(np.float32), prepend=0) * np.exp(-t * 55.0) * 0.08
    return (body + click).astype(np.float32)


def _snare(sr: int) -> np.ndarray:
    n = int(sr * 0.18)
    t = np.arange(n) / sr
    noise = np.diff(np.random.randn(n).astype(np.float32), prepend=0)
    tone = np.sin(2 * np.pi * 185.0 * t)
    return ((0.8 * noise + 0.2 * tone) * np.exp(-t * 17.0)).astype(np.float32)


def _hat(sr: int, open_hat: bool = False) -> np.ndarray:
    n = int(sr * (0.16 if open_hat else 0.05))
    t = np.arange(n) / sr
    x = np.diff(np.random.randn(n).astype(np.float32), prepend=0)
    return (x * np.exp(-t * (14.0 if open_hat else 50.0))).astype(np.float32)


def _tom(sr: int, freq: float = 120.0) -> np.ndarray:
    n = int(sr * 0.2)
    t = np.arange(n) / sr
    wave = np.sin(2 * np.pi * freq * t) * np.exp(-t * 9.0)
    return (wave * _env(n, sr, 0.002, 0.12)).astype(np.float32)


def _tone(freq: float, n: int, sr: int, kind: str = "sine") -> np.ndarray:
    t = np.arange(n) / sr
    if kind == "square":
        wave = np.sign(np.sin(2 * np.pi * freq * t)) * 0.25 + np.sin(2 * np.pi * freq * t) * 0.75
    elif kind == "saw":
        wave = 2.0 * ((freq * t) % 1.0) - 1.0
        wave = wave * 0.55 + np.sin(2 * np.pi * freq * t) * 0.45
    elif kind == "pad":
        wave = np.sin(2 * np.pi * freq * t)
        wave += 0.32 * np.sin(2 * np.pi * freq * 2 * t)
        wave += 0.1 * np.sin(2 * np.pi * freq * 3 * t)
    else:
        wave = np.sin(2 * np.pi * freq * t)
        wave += 0.15 * np.sin(2 * np.pi * freq * 2 * t)
    return (wave * _env(n, sr)).astype(np.float32)


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
    return (out * _env(n, sr, 0.003, 0.1)).astype(np.float32)


def _chord_tones(root_midi: int, genre: str) -> tuple[int, int, int]:
    if genre == "lofi":
        return root_midi, root_midi + 4, root_midi + 7
    return root_midi, root_midi + 3, root_midi + 7


def _sidechain(bus: np.ndarray, kick_env: np.ndarray, amount: float = 0.35) -> np.ndarray:
    duck = 1.0 - amount * np.clip(kick_env, 0.0, 1.0)
    return (bus * duck).astype(np.float32)


def _master_glue(audio: np.ndarray, sr: int, genre: str) -> np.ndarray:
    x = audio.astype(np.float32)
    spec = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(len(x), 1 / sr)
    if genre == "pop":
        # Target: Şehir Akıyor-style dense sub, dark top (sub/mid ~6, hi/mid ~0.12)
        spec[freqs < 150] *= 3.4
        spec[(freqs >= 150) & (freqs < 420)] *= 1.75
        spec[(freqs >= 420) & (freqs < 2500)] *= 1.12
        spec[freqs > 4500] *= 0.52
    elif genre in BEAT_GENRES:
        spec[freqs < 120] *= 1.8
        spec[(freqs >= 120) & (freqs < 400)] *= 1.25
        spec[freqs > 5000] *= 0.72
    else:
        spec[freqs < 45] *= 0.55
    x = np.fft.irfft(spec, n=len(x)).astype(np.float32)
    win = max(int(sr * 0.015), 32)
    env = np.sqrt(np.convolve(x**2, np.ones(win) / win, mode="same") + 1e-9)
    thresh = float(np.percentile(env, 70) + 1e-6)
    gain = np.clip(thresh / (env + 1e-6), 0.6, 2.0)
    drive = 1.35 if genre == "pop" else 1.15
    x = np.tanh(x * gain * drive).astype(np.float32)
    peak = float(np.max(np.abs(x)) + 1e-8)
    return np.clip(x / peak * 0.94, -1, 1)


def parse_instruments(raw: str | None, genre: str) -> list[str]:
    style = STYLES.get(genre, STYLES["pop"])
    parts = [p.strip().lower() for p in (raw or "").split(",") if p.strip()]
    picked = [p for p in parts if p in ALLOWED]
    return picked or list(style["default"])


def render_sub_layer(
    genre: str,
    n: int,
    sr: int,
    bpm: float,
    offset: int = 0,
    groove: str | None = None,
) -> np.ndarray:
    """808 + kick grid to reinforce catalog loops toward urban production weight."""
    style = STYLES.get(genre, STYLES["pop"])
    pattern = resolve_groove(genre, groove)
    root = int(style["root"])
    chords = style["chords"]
    step = 60.0 / bpm / 4.0
    layer = np.zeros(n, dtype=np.float32)
    kick = _kick(sr)
    kick_hits = set(pattern["kick"])
    i = 0
    while True:
        at = int(i * step * sr) + offset
        if at >= n:
            break
        bar_pos = i % 16
        chord_root = root + int(chords[(i // 16) % len(chords)])
        sub_note = _sub808(sr, chord_root - 24)
        if bar_pos in kick_hits:
            _place(layer, kick, at, 0.55)
            _place(layer, sub_note, at, 0.85)
        i += 1
    return layer.astype(np.float32)


def finish_production(
    audio: np.ndarray,
    sr: int,
    genre: str,
    vocal: np.ndarray | None = None,
) -> np.ndarray:
    del vocal  # sidechain belongs in mix.py — ducking here buried the beat
    mix = _master_glue(audio.astype(np.float32), sr, genre)
    fade = min(int(sr * 0.05), len(mix) // 10)
    if fade:
        mix[:fade] *= np.linspace(0, 1, fade)
        mix[-fade:] *= np.linspace(1, 0, fade)
    return mix.astype(np.float32)


def render_bed(
    genre: str,
    instruments: list[str],
    n: int,
    sr: int = 44100,
    bpm: float | None = None,
    offset: int = 0,
    ambient: bool = False,
    vocal: np.ndarray | None = None,
    groove: str | None = None,
) -> np.ndarray:
    style = STYLES.get(genre, STYLES["pop"])
    pattern = resolve_groove(genre, groove)
    bpm = float(bpm) if bpm and bpm >= 40 else float(pattern["bpm"])
    offset = max(int(offset), 0)
    root = int(style["root"])
    chords = style["chords"]
    swing = float(pattern.get("swing", style["swing"]))
    step = 60.0 / bpm / 4.0
    if not instruments:
        instruments = list(style["default"])
    want = set(instruments)
    if ambient and genre in {"slow", "lofi"}:
        want.discard("drums")

    profile = style.get("profile", "standard")
    urban = profile == "urban" or genre == "pop"
    kick_hits = set(pattern["kick"])
    snare_hits = set(pattern["snare"])
    open_hits = set(pattern["open_hat"])
    tom_hits = set(pattern["tom"])
    hat_mode = str(pattern.get("hat") or "8th")
    use_clap = bool(pattern.get("clap"))

    drums = np.zeros(n, dtype=np.float32)
    bass = np.zeros(n, dtype=np.float32)
    harmony = np.zeros(n, dtype=np.float32)
    texture = np.zeros(n, dtype=np.float32)
    kick_env = np.zeros(n, dtype=np.float32)

    kick = _kick(sr) if "drums" in want else None
    snare = _snare(sr) if "drums" in want else None
    hat = _hat(sr) if "drums" in want else None
    clap = _clap(sr) if "drums" in want and use_clap else None
    open_hat = _hat(sr, True) if "drums" in want and open_hits else None
    tom = _tom(sr) if "drums" in want and tom_hits else None
    sub808 = _sub808(sr) if "bass" in want and urban else None

    i = 0
    while True:
        t = i * step
        if swing and i % 2 == 1:
            t += step * swing
        at = int(t * sr) + offset
        if at >= n:
            break
        bar_pos = i % 16
        bar_num = i // 16
        chord_idx = bar_num % len(chords)
        chord_root = root + int(chords[chord_idx])
        notes = _chord_tones(chord_root, genre)
        eighth = int(step * sr * 2)
        quarter = int(step * sr * 4)

        if kick is not None and bar_pos in kick_hits:
            _place(drums, kick, at, 0.82 if urban else 0.9)
            end = min(n, at + len(kick))
            kick_env[at:end] = np.maximum(kick_env[at:end], np.linspace(1, 0, end - at))
            if sub808 is not None:
                note = _sub808(sr, chord_root - 24)
                _place(bass, note, at, 1.0)

        if snare is not None and bar_pos in snare_hits:
            _place(drums, snare, at, 0.52 if urban else 0.58)
            if clap is not None:
                _place(drums, clap, at, 0.38)

        if hat is not None and _hat_hit(hat_mode, bar_pos):
            if hat_mode == "16th" or urban:
                gain = 0.2 + (0.06 if bar_pos % 4 == 0 else 0.0)
            else:
                gain = 0.24
            _place(drums, hat, at, gain)
        if open_hat is not None and bar_pos in open_hits:
            _place(drums, open_hat, at, 0.2)

        if tom is not None and bar_pos in tom_hits:
            _place(drums, tom, at, 0.22)

        if "perc" in want:
            if bar_pos % 2 == 1:
                shaker = _hat(sr)
                _place(drums, shaker, at, 0.11)
            if bar_pos in {6, 14}:
                _place(drums, _clap(sr), at, 0.16)

        if "bass" in want and not urban:
            if genre == "trap" and bar_pos in {0, 6, 10}:
                blen = min(eighth, n - at)
                wave = _tone(_midi_hz(chord_root - 12), blen, sr, "square")
                _place(bass, wave, at, 0.38)
            elif bar_pos in {0, 4, 8, 12}:
                blen = min(quarter, n - at)
                wave = _tone(_midi_hz(chord_root - 12), blen, sr, "sine")
                _place(bass, wave, at, 0.36)

        if "keys" in want and bar_pos in {0, 8} | (set() if urban else {4, 12}):
            blen = min(eighth if urban else quarter, n - at)
            stab = np.zeros(blen, dtype=np.float32)
            for midi in notes:
                stab += _tone(_midi_hz(midi + 12), blen, sr, "sine")
            _place(harmony, stab / 3.0, at, 0.16 if urban else 0.24)

        if "guitar" in want and bar_pos % 2 == 0:
            blen = min(eighth, n - at)
            pluck = _pluck(_midi_hz(notes[bar_pos % 3]), blen, sr)
            _place(harmony, pluck, at, 0.22)

        if "pad" in want and bar_pos == 0:
            plen = int(min(n - at, step * sr * 16))
            pad = np.zeros(plen, dtype=np.float32)
            for midi in notes:
                pad += _tone(_midi_hz(midi), plen, sr, "pad")
            _place(texture, pad / 3.0, at, 0.16 if urban else 0.22)

        if "strings" in want and bar_pos == 0:
            plen = int(min(n - at, step * sr * 16))
            layer = np.zeros(plen, dtype=np.float32)
            for midi in (notes[0] + 12, notes[2] + 12):
                layer += _tone(_midi_hz(midi), plen, sr, "pad")
            _place(texture, layer / 2.0, at, 0.18)

        if "synth" in want and bar_pos % 4 == 0:
            blen = min(eighth, n - at)
            hook_midi = notes[0] + 12
            if bar_pos in {8}:
                hook_midi = notes[1] + 12
            wave = _tone(_midi_hz(hook_midi), blen, sr, "saw")
            _place(texture, wave, at, 0.16 if urban else 0.14)

        if "brass" in want and bar_pos in {0, 8}:
            blen = min(int(step * sr * 3), n - at)
            horn = np.zeros(blen, dtype=np.float32)
            for midi in (notes[0] + 12, notes[1] + 12, notes[2] + 12):
                horn += _tone(_midi_hz(midi), blen, sr, "saw")
            _place(harmony, horn / 3.0, at, 0.2)

        i += 1

    bass = _sidechain(bass, kick_env, 0.35 if urban else 0.42)
    texture = _sidechain(texture, kick_env, 0.22 if urban else 0.28)
    harmony = _sidechain(harmony, kick_env, 0.12 if urban else 0.18)

    drums_g = 1.08 if "drums" in want or "perc" in want else 0.0
    bass_g = 1.18 if "bass" in want else 0.0
    harm_g = 0.95 if want & {"keys", "guitar", "brass"} else 0.55
    tex_g = 0.9 if want & {"pad", "synth", "strings"} else 0.45
    session = drums * drums_g + bass * bass_g + harmony * harm_g + texture * tex_g
    return finish_production(session, sr, genre, vocal)


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
    groove: str | None = None,
) -> Path:
    return write_wav(
        dest,
        render_bed(
            genre,
            instruments,
            n,
            sr,
            bpm=bpm,
            offset=offset,
            ambient=ambient,
            vocal=vocal,
            groove=groove,
        ),
        sr,
    )
