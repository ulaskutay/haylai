from __future__ import annotations

import inspect
import os
import traceback
from functools import lru_cache
from pathlib import Path

import numpy as np

from pipeline.audio import use_gpu_models, write_wav
from pipeline.bed import ALLOWED, STYLES, finish_production, render_sub_layer

GENRE_FRAMES: dict[str, str] = {
    "pop": (
        "radio-ready dark urban pop instrumental arrangement, {key}, {bpm} BPM, "
        "wide stereo, dense mix, punchy and modern, instrumental only"
    ),
    "trap": (
        "hard trap instrumental arrangement, {key}, {bpm} BPM, cinematic and heavy, "
        "wide stereo, instrumental only"
    ),
    "rock": (
        "modern rock band instrumental arrangement, {key}, {bpm} BPM, stadium energy, "
        "tight live room, instrumental only"
    ),
    "lofi": (
        "lofi hip hop instrumental arrangement, {key}, {bpm} BPM, dusty night vibe, "
        "warm and intimate, instrumental only"
    ),
    "slow": (
        "slow emotional ballad instrumental arrangement, {key}, {bpm} BPM, romantic, "
        "cinematic space, instrumental only"
    ),
}

GENRE_KEYS: dict[str, str] = {
    "pop": "A minor",
    "trap": "F minor",
    "rock": "E minor",
    "lofi": "C major",
    "slow": "D minor",
}

GROOVE_HINTS: dict[str, str] = {
    "pop-four": "four-on-the-floor kick on one and three, claps on two and four",
    "pop-sync": "syncopated urban pop groove, late kicks, walking pocket",
    "pop-clap": "sparse verse drums, loud chorus claps",
    "trap-roll": "rolling trap hats, syncopated 808 kicks",
    "trap-drill": "sparse drill kicks, sliding 808 feel",
    "trap-bounce": "bouncy trap groove with extra kick pickups",
    "rock-four": "four-on-the-floor live rock drums",
    "rock-drive": "driving rock drums with tom fills",
    "rock-half": "half-time rock groove, heavy snare",
    "lofi-boom": "dusty boom bap, late second kick, swung hats",
    "lofi-dust": "soft lofi night beat, light kick",
    "lofi-soft": "minimal lofi pulse, drums in the back",
    "slow-pulse": "slow heart-pulse kick on one and three",
    "slow-side": "half-time ballad groove, wide space",
    "slow-heart": "syncopated slow arabesque-pop pulse",
}

INSTRUMENT_HINTS: dict[str, str] = {
    "drums": "full drum kit as the pulse: punchy kick, snare, crisp hi-hats, stereo room",
    "perc": "layered percussion pocket: shakers, congas, claps, ghost hits",
    "bass": "deep 808 and electric bass locked to the kick, sub-heavy groove",
    "keys": "rich piano and electric keys, wide chord voicings and rhythmic stabs",
    "guitar": "electric guitar rhythm chops, muted riffs, and harmonic color",
    "pad": "wide evolving atmospheric pads filling the stereo bed",
    "synth": "analog synth leads and plucks carrying a memorable hook",
    "strings": "cinematic string ensemble, legato lines and swells",
    "brass": "bold horn section stabs and brass hits on the downbeats",
}

INSTRUMENT_SHORT: dict[str, str] = {
    "drums": "punchy drums",
    "perc": "shakers claps percussion",
    "bass": "deep 808 bass",
    "keys": "piano and keys",
    "guitar": "electric guitar",
    "pad": "wide pads",
    "synth": "synth lead",
    "strings": "cinematic strings",
    "brass": "horn brass stabs",
}

ABSENT_HINTS: dict[str, str] = {
    "drums": "no drums, no kick, no snare, no hi-hats, no drum kit",
    "perc": "no extra percussion, no shaker, no conga",
    "bass": "no bass, no 808, no sub bass",
    "keys": "no piano, no keys, no electric piano",
    "guitar": "no guitar, no electric guitar",
    "pad": "no pads, no atmosphere bed",
    "synth": "no synth lead, no pluck synth",
    "strings": "no strings, no orchestra, no violin",
    "brass": "no brass, no horns, no trumpet",
}

NEGATIVE_PROMPT = (
    "low quality, muddy, noisy, amateur, vocals, singing, voice, speech, acapella, "
    "distortion, clipping, mono, thin, weak bass"
)


def ml_bed_enabled() -> bool:
    if not use_gpu_models():
        return False
    return os.environ.get("BED_ML_ENABLED", "true").lower() in {"1", "true", "yes"}


def bed_mode() -> str:
    return os.environ.get("BED_MODE", "auto").lower()


def prefer_ml_on_gpu() -> bool:
    return use_gpu_models() and bed_mode() == "auto"


def bed_engine_chain() -> list[str]:
    configured = os.environ.get("BED_ENGINE", "auto").lower()
    if configured == "auto":
        return ["acestep", "stable-audio", "musicgen"]
    if configured in {"acestep", "stable-audio", "musicgen"}:
        return [configured]
    return ["acestep", "stable-audio", "musicgen"]


def _picked_instruments(genre: str, instruments: list[str]) -> list[str]:
    style = STYLES.get(genre, STYLES["pop"])
    picked = [item for item in instruments if item in ALLOWED]
    return picked or list(style["default"])


def build_prompt(
    genre: str,
    bpm: float,
    instruments: list[str],
    groove: str = "",
    compact: bool = False,
) -> str:
    style = STYLES.get(genre, STYLES["pop"])
    resolved_bpm = bpm if bpm >= 40 else float(style["bpm"])
    key = GENRE_KEYS.get(genre, "A minor")
    frame = GENRE_FRAMES.get(genre, GENRE_FRAMES["pop"]).format(
        bpm=int(round(resolved_bpm)),
        key=key,
    )
    picked = _picked_instruments(genre, instruments)
    missing = [item for item in ALLOWED if item not in set(picked)]
    groove_hint = GROOVE_HINTS.get((groove or "").strip())
    if compact:
        featured = ", ".join(INSTRUMENT_SHORT.get(item, item) for item in picked)
        bits = [frame, f"only {featured}", "no vocals"]
        if groove_hint:
            bits.append(groove_hint)
        if missing:
            bits.append("no " + ", ".join(missing))
        return ", ".join(bits)[:240]
    featured = ". ".join(
        f"{i + 1}) {INSTRUMENT_HINTS.get(item, item)}" for i, item in enumerate(picked)
    )
    omit = ", ".join(ABSENT_HINTS[item] for item in missing if item in ABSENT_HINTS)
    parts = [
        f"Instrumental arrangement featuring ONLY {', '.join(picked)}.",
        featured,
        frame,
        "Dense professional stereo mix, radio-ready, layered, no vocals, no singing, no speech.",
    ]
    if groove_hint:
        parts.append(groove_hint)
    if omit:
        parts.append(f"Absolutely no other instruments. Strictly omit: {omit}.")
    return " ".join(parts)


def build_negative(genre: str, instruments: list[str]) -> str:
    picked = set(_picked_instruments(genre, instruments))
    extra = [
        ABSENT_HINTS[item]
        for item in ALLOWED
        if item not in picked and item in ABSENT_HINTS
    ]
    if extra:
        return f"{NEGATIVE_PROMPT}, {', '.join(extra)}"
    return NEGATIVE_PROMPT


def _max_seconds() -> float:
    try:
        return float(os.environ.get("BED_MAX_SECONDS", "60"))
    except ValueError:
        return 60.0


def _resample(audio: np.ndarray, src_sr: int, dst_sr: int) -> np.ndarray:
    if src_sr == dst_sr:
        return audio.astype(np.float32)
    import librosa

    return librosa.resample(audio.astype(np.float32), orig_sr=src_sr, target_sr=dst_sr)


def _to_mono(wav: np.ndarray) -> np.ndarray:
    if wav.ndim == 1:
        return wav.astype(np.float32)
    return wav.mean(axis=0).astype(np.float32)


def _normalize_stereo(wav: np.ndarray) -> np.ndarray:
    if wav.ndim == 1:
        return wav.astype(np.float32)
    if wav.shape[0] <= 8 and wav.shape[0] < wav.shape[1]:
        return wav.astype(np.float32)
    return wav.T.astype(np.float32)


def _loop_crossfade(audio: np.ndarray, n: int, sr: int) -> np.ndarray:
    if len(audio) >= n:
        return audio[:n].astype(np.float32)
    xf = min(int(sr * 1.5), len(audio) // 4, max(n - len(audio), 1))
    if xf < 64:
        reps = int(np.ceil(n / max(len(audio), 1)))
        return np.tile(audio, reps)[:n].astype(np.float32)

    out = audio.astype(np.float32).copy()
    while len(out) < n:
        tail = out[-xf:]
        head = audio[:xf]
        blend = tail * np.linspace(1, 0, xf) + head * np.linspace(0, 1, xf)
        out = np.concatenate([out[:-xf], blend, audio[xf:]])
    return out[:n].astype(np.float32)


def _postprocess_bed(
    wav: np.ndarray,
    gen_sr: int,
    sr: int,
    n: int,
    genre: str,
    bpm: float,
    vocal: np.ndarray | None,
    sub_mix: float,
    groove: str = "",
) -> np.ndarray:
    wav = _to_mono(_normalize_stereo(wav))
    wav = _resample(wav, gen_sr, sr)
    wav = _loop_crossfade(wav, n, sr)
    if genre in {"pop", "trap"} and bpm >= 40 and sub_mix > 0:
        sub = render_sub_layer(genre, len(wav), sr, bpm, offset=0, groove=groove)
        wav = np.clip(wav + sub * sub_mix, -1.0, 1.0)
    return finish_production(wav, sr, genre, None)


@lru_cache(maxsize=1)
def _load_acestep():
    import torch
    from diffusers import AceStepPipeline

    model_id = os.environ.get("ACESTEP_MODEL", "ACE-Step/acestep-v15-xl-turbo-diffusers")
    pipe = AceStepPipeline.from_pretrained(
        model_id,
        torch_dtype=torch.float16,
    )
    return pipe.to("cuda")


@lru_cache(maxsize=1)
def _load_stable_audio():
    import torch
    from diffusers import StableAudioPipeline

    model_id = os.environ.get("STABLE_AUDIO_MODEL", "stabilityai/stable-audio-open-1.0")
    pipe = StableAudioPipeline.from_pretrained(model_id, torch_dtype=torch.float16)
    return pipe.to("cuda")


@lru_cache(maxsize=1)
def _load_musicgen():
    import torch
    from transformers import AutoProcessor, MusicgenForConditionalGeneration

    model_id = os.environ.get("MUSICGEN_MODEL", "facebook/musicgen-medium")
    processor = AutoProcessor.from_pretrained(model_id)
    model = MusicgenForConditionalGeneration.from_pretrained(model_id, torch_dtype=torch.float16)
    model = model.to("cuda")
    model.eval()
    return processor, model


def _generate_acestep(
    prompt: str,
    duration: float,
    bpm: float,
    keyscale: str,
    genre: str,
    instruments: list[str],
) -> tuple[np.ndarray, int]:
    pipe = _load_acestep()
    steps = int(os.environ.get("ACESTEP_STEPS", "8"))
    picked = _picked_instruments(genre, instruments)
    kwargs: dict = {
        "prompt": prompt,
        "lyrics": "[Instrumental]",
        "audio_duration": duration,
        "bpm": int(round(bpm)),
        "keyscale": keyscale,
        "timesignature": "4",
        "num_inference_steps": steps,
    }
    try:
        params = inspect.signature(pipe.__call__).parameters
    except (TypeError, ValueError):
        params = {}
    if "instruction" in params:
        kwargs["instruction"] = (
            f"Instrumental only. Play only: {', '.join(picked)}. No unlisted instruments."
        )
    result = pipe(**kwargs)
    wav = result.audios[0].float().cpu().numpy()
    return _normalize_stereo(wav), 48000


def _generate_stable_audio(
    prompt: str,
    duration: float,
    genre: str,
    instruments: list[str],
) -> tuple[np.ndarray, int]:
    pipe = _load_stable_audio()
    steps = int(os.environ.get("STABLE_AUDIO_STEPS", "100"))
    result = pipe(
        prompt,
        negative_prompt=build_negative(genre, instruments),
        num_inference_steps=steps,
        audio_end_in_s=duration,
        num_waveforms_per_prompt=1,
    )
    wav = result.audios[0].T.float().cpu().numpy()
    return wav, int(pipe.vae.sampling_rate)


def _generate_musicgen(prompt: str, duration: float) -> tuple[np.ndarray, int]:
    processor, model = _load_musicgen()
    import torch

    inputs = processor(text=[prompt], padding=True, return_tensors="pt").to("cuda")
    max_new_tokens = int(min(max(duration, 4.0) * 51, 2048))
    guidance = float(os.environ.get("MUSICGEN_GUIDANCE", "4.5"))

    with torch.inference_mode():
        audio_values = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            guidance_scale=guidance,
        )

    wav = audio_values[0].cpu().numpy().astype(np.float32)
    if wav.ndim > 1:
        wav = _to_mono(wav)
    return wav, int(model.config.audio_encoder.sampling_rate)


def warmup() -> None:
    if not ml_bed_enabled():
        return
    for engine in bed_engine_chain():
        try:
            if engine == "acestep":
                _load_acestep()
            elif engine == "stable-audio":
                _load_stable_audio()
            else:
                _load_musicgen()
            return
        except Exception:
            continue


def generate_bed(
    dest: Path,
    genre: str,
    instruments: list[str],
    n: int,
    sr: int,
    bpm: float,
    vocal: np.ndarray | None = None,
    engine: str = "acestep",
    groove: str = "",
) -> Path:
    style = STYLES.get(genre, STYLES["pop"])
    resolved_bpm = bpm if bpm >= 40 else float(style["bpm"])
    prompt = build_prompt(
        genre,
        resolved_bpm,
        instruments,
        groove,
        compact=engine == "acestep",
    )
    keyscale = GENRE_KEYS.get(genre, "A minor")
    target_sec = n / sr
    duration = min(_max_seconds(), target_sec)
    duration = max(duration, 10.0)

    if engine == "stable-audio":
        duration = min(duration, 47.0)
        wav, gen_sr = _generate_stable_audio(prompt, duration, genre, instruments)
        sub_mix = 0.3
    elif engine == "musicgen":
        duration = min(duration, 45.0)
        wav, gen_sr = _generate_musicgen(prompt, duration)
        sub_mix = 0.38
    else:
        wav, gen_sr = _generate_acestep(
            prompt, duration, resolved_bpm, keyscale, genre, instruments
        )
        sub_mix = 0.38

    wav = _postprocess_bed(wav, gen_sr, sr, n, genre, resolved_bpm, vocal, sub_mix, groove)
    return write_wav(dest, wav, sr)


def try_generate_bed(
    dest: Path,
    genre: str,
    instruments: list[str],
    n: int,
    sr: int,
    bpm: float,
    vocal: np.ndarray | None = None,
    groove: str = "",
) -> tuple[Path | None, str | None]:
    if bed_mode() == "catalog":
        return None, None
    if not ml_bed_enabled():
        return None, None

    for engine in bed_engine_chain():
        for _ in range(2):
            try:
                return generate_bed(
                    dest,
                    genre,
                    instruments,
                    n,
                    sr,
                    bpm,
                    vocal,
                    engine=engine,
                    groove=groove,
                ), engine
            except Exception:
                print(f"bed AI {engine} failed", flush=True)
                traceback.print_exc()
                continue
    return None, None
