from __future__ import annotations

import time
from pathlib import Path
from tempfile import TemporaryDirectory

from pipeline.audio import download, to_wav, upload_bytes
from pipeline.callback import notify
from pipeline.clean import clean
from pipeline.export import export_mp3
from pipeline.mix import mix
from pipeline.pitch import correct_pitch
from pipeline.rvc import convert
from pipeline.types import STEPS, JobPayload


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
            bed_raw = download(payload.instrumental_url, workdir / "bed.bin")
            original = to_wav(original_raw, workdir / "original.wav")
            bed = to_wav(bed_raw, workdir / "bed.wav")
            time.sleep(0.12)

            report("cleaning")
            cleaned = clean(original, workdir)
            time.sleep(0.12)

            report("pitch")
            pitched = correct_pitch(cleaned, workdir)
            time.sleep(0.12)

            report("rvc")
            converted = convert(pitched, workdir)
            time.sleep(0.12)

            report("mix")
            mixed = mix(converted, bed, workdir)
            time.sleep(0.12)

            report("export")
            mp3 = export_mp3(mixed)
            upload_bytes(payload.upload_url, mp3, "audio/mpeg")
            report("export", status="completed")
            return {
                "ok": True,
                "song_id": payload.song_id,
                "steps": list(STEPS),
                "bytes": len(mp3),
            }
        except Exception as exc:
            report("export", status="failed", extra={"error_message": str(exc)})
            raise
