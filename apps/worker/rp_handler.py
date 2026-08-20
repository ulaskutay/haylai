import sys
import traceback
from pathlib import Path

print("hayl worker boot", flush=True)

ROOT = Path(__file__).resolve().parent
for candidate in (ROOT, ROOT / "apps" / "worker"):
    if (candidate / "pipeline").is_dir():
        sys.path.insert(0, str(candidate))
        break
else:
    sys.path.insert(0, str(ROOT))

try:
    import runpod
    from pipeline.job import run_bed_loop, run_job
    from pipeline.types import JobPayload
except Exception:
    traceback.print_exc()
    sys.stdout.flush()
    sys.stderr.flush()
    raise


def handler(event):
    inp = event.get("input") or event
    try:
        payload = JobPayload.from_dict(inp if isinstance(inp, dict) else {})
        if payload.task == "bed_loop":
            return run_bed_loop(payload)
        return run_job(payload)
    except Exception as exc:
        traceback.print_exc()
        song_id = ""
        if isinstance(inp, dict):
            song_id = str(inp.get("song_id") or "")
        return {"ok": False, "song_id": song_id, "error": str(exc)}


if __name__ == "__main__":
    print("runpod serverless listening (models load on first job)", flush=True)
    runpod.serverless.start({"handler": handler})
