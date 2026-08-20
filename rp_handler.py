import sys
from pathlib import Path

import runpod

sys.path.insert(0, str(Path(__file__).resolve().parent / "apps" / "worker"))

from pipeline.job import run_job
from pipeline.types import JobPayload


def handler(event):
    inp = event.get("input") or event
    try:
        payload = JobPayload.from_dict(inp)
        return run_job(payload)
    except Exception as exc:
        song_id = ""
        if isinstance(inp, dict):
            song_id = str(inp.get("song_id") or "")
        return {"ok": False, "song_id": song_id, "error": str(exc)}


if __name__ == '__main__':
    runpod.serverless.start({'handler': handler })
