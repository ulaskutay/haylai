from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from pipeline.bed import STYLES

BPM_RANGE: dict[str, tuple[float, float]] = {
    "pop": (86.0, 98.0),
    "trap": (128.0, 152.0),
    "rock": (108.0, 132.0),
    "lofi": (72.0, 96.0),
    "slow": (56.0, 78.0),
}


@dataclass
class RhythmPlan:
    bpm: float
    offset: int
    confidence: float
    ambient: bool


def fold_bpm(raw: float, genre: str) -> float:
    style = STYLES.get(genre, STYLES["pop"])
    default = float(style["bpm"])
    lo, hi = BPM_RANGE.get(genre, (default * 0.85, default * 1.15))
    bpm = float(raw)
    if not np.isfinite(bpm) or bpm < 40:
        return default
    for _ in range(4):
        if bpm < lo:
            bpm *= 2.0
        elif bpm > hi:
            bpm /= 2.0
        else:
            break
    return float(np.clip(bpm, lo, hi))


def _onset_times(y: np.ndarray, sr: int) -> np.ndarray:
    import librosa

    env = librosa.onset.onset_strength(y=y, sr=sr)
    onsets = librosa.onset.onset_detect(onset_envelope=env, sr=sr, units="time", backtrack=True)
    return np.asarray(onsets, dtype=np.float64)


def _estimate_bpm(onsets: np.ndarray, genre: str, y: np.ndarray, sr: int) -> tuple[float, float]:
    style = STYLES.get(genre, STYLES["pop"])
    default = float(style["bpm"])
    if len(onsets) < 3:
        return default, 0.0

    candidates: list[float] = [default]
    iois = np.diff(onsets)
    iois = iois[(iois > 0.18) & (iois < 2.2)]
    if len(iois):
        for div in (1, 2, 4):
            bpms = 60.0 / (iois * div)
            candidates.extend(bpms.tolist())

    try:
        import librosa

        env = librosa.onset.onset_strength(y=y, sr=sr)
        tempos = librosa.feature.rhythm.tempo(onset_envelope=env, sr=sr, aggregate=None)
        if tempos is not None and len(np.atleast_1d(tempos)):
            candidates.extend(np.atleast_1d(tempos).tolist())
    except Exception:
        pass

    scored: list[tuple[float, float]] = []
    for raw in candidates:
        bpm = fold_bpm(float(raw), genre)
        if not np.isfinite(bpm):
            continue
        beat = 60.0 / bpm
        err = 0.0
        for t in onsets:
            phase = (t - onsets[0]) % beat
            err += min(phase, beat - phase)
        err /= max(len(onsets), 1)
        scored.append((err, bpm))

    if not scored:
        return default, 0.0

    scored.sort(key=lambda item: item[0])
    best_err, best_bpm = scored[0]
    second_err = scored[1][0] if len(scored) > 1 else best_err + 0.05
    spread = max(second_err - best_err, 1e-3)
    confidence = float(np.clip(1.0 - best_err / 0.12, 0.0, 1.0) * np.clip(spread / 0.04, 0.2, 1.0))
    return best_bpm, confidence


def _align_offset(onsets: np.ndarray, bpm: float, sr: int, n: int) -> int:
    if len(onsets) == 0 or bpm <= 0:
        return 0
    beat = 60.0 / bpm
    best_offset = 0
    best_score = float("inf")
    steps = max(int(beat * sr / 64), 1)
    for step in range(steps + 1):
        offset = int(step * beat * sr / steps)
        score = 0.0
        for t in onsets:
            rel = t - offset / sr
            if rel < 0:
                score += 0.08
                continue
            phase = rel % beat
            score += min(phase, beat - phase)
        score /= max(len(onsets), 1)
        if score < best_score:
            best_score = score
            best_offset = offset
    return int(np.clip(best_offset, 0, n - 1))


def analyze_rhythm(
    audio: np.ndarray,
    sr: int,
    genre: str,
    mode: str,
    bpm_hint: float = 0.0,
) -> RhythmPlan:
    style = STYLES.get(genre, STYLES["pop"])
    default_bpm = float(style["bpm"])
    n = len(audio)
    mode = (mode or "follow").lower()

    if mode in {"style", "lock"}:
        return RhythmPlan(bpm=default_bpm, offset=0, confidence=1.0, ambient=genre in {"slow", "lofi"})

    if bpm_hint >= 40:
        bpm = fold_bpm(bpm_hint, genre)
        return RhythmPlan(bpm=bpm, offset=0, confidence=0.8, ambient=False)

    if n < sr // 2:
        return RhythmPlan(bpm=default_bpm, offset=0, confidence=0.0, ambient=True)

    try:
        y = audio.astype(np.float32)
        onsets = _onset_times(y, sr)
        if len(onsets) == 0:
            return RhythmPlan(bpm=default_bpm, offset=0, confidence=0.0, ambient=True)

        bpm, confidence = _estimate_bpm(onsets, genre, y, sr)
        offset = _align_offset(onsets, bpm, sr, n)

        if confidence < 0.35:
            bpm = default_bpm
            offset = _align_offset(onsets, bpm, sr, n)
            # Beat genres keep full drums even when timing is uncertain.
            ambient = genre in {"slow", "lofi"}
        else:
            ambient = genre in {"slow", "lofi"} and confidence < 0.55

        return RhythmPlan(bpm=bpm, offset=offset, confidence=confidence, ambient=ambient)
    except Exception:
        return RhythmPlan(bpm=default_bpm, offset=0, confidence=0.0, ambient=True)


def resolve_bpm(audio: np.ndarray, sr: int, genre: str, mode: str, bpm_hint: float = 0.0) -> tuple[float, int]:
    plan = analyze_rhythm(audio, sr, genre, mode, bpm_hint)
    return plan.bpm, plan.offset
