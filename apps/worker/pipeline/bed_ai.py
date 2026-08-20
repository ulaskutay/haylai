from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import numpy as np

from pipeline.audio import use_gpu_models, write_wav
from pipeline.bed import STYLES, finish_production, render_sub_layer

GENRE_PROMPTS: dict[str, str] = {
    "pop": (
        "dark urban pop production, heavy 808 sub bass, crisp trap hi-hats, snare clap, "
        "moody minor key, {bpm} BPM, wide stereo, radio-ready mix, instrumental only, no vocals"
    ),
    "trap": (
        "hard trap beat, distorted 808 bass, fast rolling hi-hats, dark cinematic, "
        "{bpm} BPM, wide stereo, instrumental only, no vocals"
    ),
    "rock": (
        "modern rock band instrumental, tight live drums, electric bass, power-chord guitars, "
        "{bpm} BPM, stadium energy, instrumental only, no vocals"
    ),
    "lofi": (
        "lofi hip hop beat, dusty mellow drums, warm rhodes piano, vinyl texture, "
        "{bpm} BPM, cozy night vibe, instrumental only, no vocals"
    ),
    "slow": (
        "slow emotional R&B instrumental, soft punchy drums, deep sub bass, lush pads and strings, "
        "{bpm} BPM, romantic, instrumental only, no vocals"
    ),
}

GENRE_KEYS: dict[str, str] = {
    "pop": "A minor",
    "trap": "F minor",
    "rock": "E minor",
    "lofi": "C major",
    "slow": "D minor",
}

INSTRUMENT_HINTS: dict[str, str] = {
    "drums": "punchy drums",
    "bass": "sub bass",
    "keys": "keyboard chords",
    "guitar": "electric guitar",
    "pad": "atmospheric pads",
    "synth": "synth lead",
    "strings": "string section",
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


def build_prompt(genre: str, bpm: float, instruments: list[str]) -> str:
    style = STYLES.get(genre, STYLES["pop"])
    resolved_bpm = bpm if bpm >= 40 else float(style["bpm"])
    template = GENRE_PROMPTS.get(genre, GENRE_PROMPTS["pop"])
    base = template.format(bpm=int(round(resolved_bpm)))
    hints = ", ".join(INSTRUMENT_HINTS.get(item, item) for item in instruments[:4])
    if hints:
        return f"{base}, with {hints}"
    return base


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
) -> np.ndarray:
    wav = _to_mono(_normalize_stereo(wav))
    wav = _resample(wav, gen_sr, sr)
    wav = _loop_crossfade(wav, n, sr)
    if genre in {"pop", "trap"} and bpm >= 40 and sub_mix > 0:
        sub = render_sub_layer(genre, len(wav), sr, bpm, offset=0)
        wav = np.clip(wav + sub * sub_mix, -1.0, 1.0)
    return finish_production(wav, sr, genre, vocal)


@lru_cache(maxsize=1)
def _load_acestep():
    import torch
    from diffusers import AceStepPipeline

    model_id = os.environ.get("ACESTEP_MODEL", "ACE-Step/acestep-v15-xl-turbo-diffusers")
    pipe = AceStepPipeline.from_pretrained(model_id, torch_dtype=torch.bfloat16)
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
) -> tuple[np.ndarray, int]:
    pipe = _load_acestep()
    steps = int(os.environ.get("ACESTEP_STEPS", "8"))
    result = pipe(
        prompt=prompt,
        lyrics="[Instrumental]",
        audio_duration=duration,
        bpm=int(round(bpm)),
        keyscale=keyscale,
        timesignature="4",
        num_inference_steps=steps,
    )
    wav = result.audios[0].float().cpu().numpy()
    return _normalize_stereo(wav), 48000


def _generate_stable_audio(prompt: str, duration: float) -> tuple[np.ndarray, int]:
    pipe = _load_stable_audio()
    steps = int(os.environ.get("STABLE_AUDIO_STEPS", "100"))
    result = pipe(
        prompt,
        negative_prompt=NEGATIVE_PROMPT,
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
) -> Path:
    style = STYLES.get(genre, STYLES["pop"])
    resolved_bpm = bpm if bpm >= 40 else float(style["bpm"])
    prompt = build_prompt(genre, resolved_bpm, instruments)
    keyscale = GENRE_KEYS.get(genre, "A minor")
    target_sec = n / sr
    duration = min(_max_seconds(), target_sec)
    duration = max(duration, 10.0)

    if engine == "stable-audio":
        duration = min(duration, 47.0)
        wav, gen_sr = _generate_stable_audio(prompt, duration)
        sub_mix = 0.3
    elif engine == "musicgen":
        duration = min(duration, 45.0)
        wav, gen_sr = _generate_musicgen(prompt, duration)
        sub_mix = 0.38
    else:
        wav, gen_sr = _generate_acestep(prompt, duration, resolved_bpm, keyscale)
        sub_mix = 0.22

    wav = _postprocess_bed(wav, gen_sr, sr, n, genre, resolved_bpm, vocal, sub_mix)
    return write_wav(dest, wav, sr)


def try_generate_bed(
    dest: Path,
    genre: str,
    instruments: list[str],
    n: int,
    sr: int,
    bpm: float,
    vocal: np.ndarray | None = None,
) -> tuple[Path | None, str | None]:
    if bed_mode() == "catalog":
        return None, None
    if not ml_bed_enabled():
        return None, None

    for engine in bed_engine_chain():
        for _ in range(2):
            try:
                return generate_bed(dest, genre, instruments, n, sr, bpm, vocal, engine=engine), engine
            except Exception:
                continue
    return None, None
