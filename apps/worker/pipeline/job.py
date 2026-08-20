from __future__ import annotations

import time
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from pipeline.audio import download, load_mono, to_wav, upload_bytes, write_wav
from pipeline.bed import parse_instruments, write_bed
from pipeline.callback import notify
from pipeline.clean import clean
from pipeline.enhance import enhance
from pipeline.export import export_mp3
from pipeline.mix import mix
from pipeline.pitch import correct_pitch
from pipeline.rhythm import analyze_rhythm
from pipeline.types import STEPS, JobPayload


def _loop_bed(src: Path, n: int, sr: int) -> Path:
    bed, _ = load_mono(src, sr=sr)
    if len(bed) >= n:
        out = bed[:n]
    else:
        reps = int(np.ceil(n / max(len(bed), 1)))
        out = np.tile(bed, reps)[:n]
    dest = src.parent / "bed-looped.wav"
    return write_wav(dest, out.astype(np.float32), sr)


def _align_loop_bed(src: Path, vocal: np.ndarray, n: int, sr: int) -> Path:
    bed, _ = load_mono(src, sr=sr)
    if len(bed) < sr:
        return _loop_bed(src, n, sr)

    import librosa

    v_env = librosa.onset.onset_strength(y=vocal.astype(np.float32), sr=sr)
    v_env = v_env / (float(np.max(v_env)) + 1e-8)
    best_start = 0
    best_corr = -1.0
    search_len = min(len(bed), sr * 12)
    hop = max(sr // 16, 512)

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


def run_job(payload: JobPayload) -> dict:
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
            converted = enhance(pitched, workdir)

            rhythm = analyze_rhythm(vocal, sr, payload.genre, payload.rhythm, payload.bpm)
            bed_path = workdir / "bed.wav"
            used_catalog = False
            # Short amateur clips fight catalog loops more than they help.
            if (
                rhythm.confidence < 0.35
                and payload.instrumental_url
                and len(vocal) >= sr * 18
            ):
                try:
                    bed_raw = download(payload.instrumental_url, workdir / "bed.bin")
                    catalog = to_wav(bed_raw, workdir / "catalog.wav")
                    bed_path = _align_loop_bed(catalog, vocal, len(vocal), sr)
                    used_catalog = True
                except Exception:
                    used_catalog = False

            if not used_catalog:
                write_bed(
                    bed_path,
                    payload.genre,
                    instruments,
                    len(vocal),
                    sr,
                    bpm=rhythm.bpm,
                    offset=rhythm.offset,
                    ambient=rhythm.ambient or rhythm.confidence < 0.35,
                    vocal=vocal,
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
                "bed_source": "catalog" if used_catalog else "generated",
            }
        except Exception as exc:
            report("export", status="failed", extra={"error_message": str(exc)})
            raise
