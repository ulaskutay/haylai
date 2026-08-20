from __future__ import annotations

import time
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from pipeline.audio import download, load_mono, to_wav, upload_bytes, write_wav
from pipeline.bed import (
    finish_production,
    parse_instruments,
    render_sub_layer,
    resolve_groove,
    write_bed,
)
from pipeline.callback import notify
from pipeline.clean import clean
from pipeline.enhance import enhance
from pipeline.rvc import convert as rvc_convert
from pipeline.export import export_mp3
from pipeline.mix import mix
from pipeline.bed_ai import prefer_ml_on_gpu, try_generate_bed
from pipeline.pitch import correct_pitch
from pipeline.rhythm import analyze_rhythm
from pipeline.types import STEPS, JobPayload

LOOP_BARS = 8
LOOP_SR = 44100


def loop_sample_count(bpm: float, bars: int = LOOP_BARS, sr: int = LOOP_SR) -> int:
    tempo = bpm if bpm and bpm >= 40 else 92.0
    return int(round(bars * 4.0 * (60.0 / tempo) * sr))


def _loop_bed(src: Path, n: int, sr: int) -> Path:
    bed, _ = load_mono(src, sr=sr)
    if len(bed) >= n:
        out = bed[:n]
    else:
        reps = int(np.ceil(n / max(len(bed), 1)))
        out = np.tile(bed, reps)[:n]
    dest = src.parent / "bed-looped.wav"
    return write_wav(dest, out.astype(np.float32), sr)


def _align_loop_bed(
    src: Path,
    vocal: np.ndarray,
    n: int,
    sr: int,
    bpm: float | None = None,
) -> Path:
    bed, _ = load_mono(src, sr=sr)
    if len(bed) < sr:
        return _loop_bed(src, n, sr)

    import librosa

    v_env = librosa.onset.onset_strength(y=vocal.astype(np.float32), sr=sr)
    v_env = v_env / (float(np.max(v_env)) + 1e-8)
    best_start = 0
    best_corr = -1.0
    search_len = min(len(bed), sr * 16)
    beat = int((60.0 / bpm) * sr) if bpm and bpm >= 40 else max(sr // 4, 1)
    hop = max(beat // 8, 256)

    for start in range(0, search_len, hop):
        segment = bed[start:]
        reps = int(np.ceil(n / max(len(segment), 1)))
        tiled = np.tile(segment, reps)[:n]
        b_env = librosa.onset.onset_strength(y=tiled.astype(np.float32), sr=sr)
        m = min(len(v_env), len(b_env))
        if m < 8:
            continue
        corr = float(np.corrcoef(v_env[:m], b_env[:m])[0, 1])
        if np.isfinite(corr) and corr > best_corr:
            best_corr = corr
            best_start = start

    segment = bed[best_start:]
    reps = int(np.ceil(n / max(len(segment), 1)))
    out = np.tile(segment, reps)[:n].astype(np.float32)
    dest = src.parent / "bed-aligned.wav"
    return write_wav(dest, out, sr)


def _produce_catalog(
    src: Path,
    vocal: np.ndarray,
    n: int,
    sr: int,
    bpm: float | None,
    genre: str,
    groove: str | None = None,
) -> Path:
    aligned = _align_loop_bed(src, vocal, n, sr, bpm=bpm)
    bed, _ = load_mono(aligned, sr=sr)
    if genre in {"pop", "trap"} and bpm and bpm >= 40:
        sub = render_sub_layer(genre, len(bed), sr, bpm, offset=0, groove=groove)
        bed = np.clip(bed.astype(np.float32) + sub * 0.55, -1.0, 1.0)
    produced = finish_production(bed, sr, genre, vocal)
    dest = src.parent / "bed-produced.wav"
    return write_wav(dest, produced, sr)


def _lock_bed(
    src: Path,
    vocal: np.ndarray,
    n: int,
    sr: int,
    genre: str,
) -> Path:
    looped = _loop_bed(src, n, sr)
    bed, _ = load_mono(looped, sr=sr)
    produced = finish_production(bed, sr, genre, vocal)
    dest = src.parent / "bed-locked.wav"
    return write_wav(dest, produced, sr)


def run_bed_loop(payload: JobPayload) -> dict:
    instruments = parse_instruments(payload.instruments, payload.genre)
    pattern = resolve_groove(payload.genre, payload.groove)
    bpm = payload.bpm if payload.bpm >= 40 else float(pattern["bpm"])
    n = loop_sample_count(bpm)
    with TemporaryDirectory(prefix="hayl-bed-") as tmp:
        workdir = Path(tmp)
        dest = workdir / "loop.wav"
        source = "procedural"
        ml_bed, ml_engine = try_generate_bed(
            dest,
            payload.genre,
            instruments,
            n,
            LOOP_SR,
            bpm,
            vocal=None,
            groove=payload.groove,
        )
        if ml_bed:
            dest = ml_bed
            source = ml_engine or "ml"
        else:
            write_bed(
                dest,
                payload.genre,
                instruments,
                n,
                LOOP_SR,
                bpm=bpm,
                offset=0,
                ambient=False,
                vocal=None,
                groove=payload.groove,
            )
            source = "procedural"
        wav_bytes = dest.read_bytes()
        upload_bytes(payload.upload_url, wav_bytes, "audio/wav")
        return {
            "ok": True,
            "song_id": payload.song_id,
            "task": "bed_loop",
            "source": source,
            "bpm": bpm,
            "bars": LOOP_BARS,
            "bytes": len(wav_bytes),
        }


def run_job(payload: JobPayload) -> dict:
    if (payload.task or "song") == "bed_loop":
        return run_bed_loop(payload)
    def report(step: str, status: str = "processing", extra: dict | None = None) -> None:
        body = {
            "song_id": payload.song_id,
            "status": status,
            "pipeline_step": step,
            **(extra or {}),
        }
        notify(payload.callback_url, payload.callback_secret, body)

    with TemporaryDirectory(prefix="hayl-") as tmp:
        workdir = Path(tmp)
        try:
            report("analyzing")
            original_raw = download(payload.original_url, workdir / "original.bin")
            original = to_wav(original_raw, workdir / "original.wav")
            instruments = parse_instruments(payload.instruments, payload.genre)

            report("cleaning")
            cleaned = clean(original, workdir)
            vocal, sr = load_mono(cleaned)

            report("pitch")
            pitched = correct_pitch(cleaned, workdir, payload.genre)

            report("rvc")
            rvc_out, rvc_applied = rvc_convert(pitched, workdir)
            converted = enhance(rvc_out, workdir, payload.genre, rvc_applied=rvc_applied)

            rhythm = analyze_rhythm(vocal, sr, payload.genre, payload.rhythm, payload.bpm)
            report("bed")
            bed_path = workdir / "bed.wav"
            bed_source = "procedural"

            if payload.lock_bed:
                if not payload.instrumental_url:
                    raise RuntimeError("lock_bed requires instrumental_url")
                bed_raw = download(payload.instrumental_url, workdir / "bed.bin")
                locked = to_wav(bed_raw, workdir / "locked-src.wav")
                bed_path = _lock_bed(locked, vocal, len(vocal), sr, payload.genre)
                bed_source = "locked"
            else:
                ml_bed, ml_engine = try_generate_bed(
                    bed_path,
                    payload.genre,
                    instruments,
                    len(vocal),
                    sr,
                    rhythm.bpm,
                    vocal,
                    groove=payload.groove,
                )
                if ml_bed:
                    bed_path = ml_bed
                    bed_source = ml_engine or "ml"
                elif payload.instrumental_url and not prefer_ml_on_gpu():
                    try:
                        bed_raw = download(payload.instrumental_url, workdir / "bed.bin")
                        catalog = to_wav(bed_raw, workdir / "catalog.wav")
                        bed_path = _produce_catalog(
                            catalog,
                            vocal,
                            len(vocal),
                            sr,
                            bpm=rhythm.bpm,
                            genre=payload.genre,
                            groove=payload.groove,
                        )
                        bed_source = "catalog"
                    except Exception:
                        pass

            if bed_source == "procedural":
                write_bed(
                    bed_path,
                    payload.genre,
                    instruments,
                    len(vocal),
                    sr,
                    bpm=rhythm.bpm,
                    offset=rhythm.offset,
                    ambient=rhythm.ambient,
                    vocal=vocal,
                    groove=payload.groove,
                )
            time.sleep(0.05)

            report("mix")
            mixed = mix(converted, bed_path, workdir, payload.genre)

            report("export")
            mp3 = export_mp3(mixed)
            upload_bytes(payload.upload_url, mp3, "audio/mpeg")
            report("export", status="completed")
            return {
                "ok": True,
                "song_id": payload.song_id,
                "steps": list(STEPS),
                "bytes": len(mp3),
                "instruments": instruments,
                "bpm": rhythm.bpm,
                "rhythm_confidence": rhythm.confidence,
                "bed_source": bed_source,
            }
        except Exception as exc:
            report("export", status="failed", extra={"error_message": str(exc)})
            raise
