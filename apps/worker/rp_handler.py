from pipeline.job import run_job
from pipeline.types import JobPayload


def handler(event: dict) -> dict:
    """RunPod serverless entrypoint. Scale-to-zero: job in, GPU up, job out."""
    inp = event.get("input") or event
    try:
        payload = JobPayload.from_dict(inp)
        return run_job(payload)
    except Exception as exc:
        song_id = ""
        if isinstance(inp, dict):
            song_id = str(inp.get("song_id") or "")
        return {"ok": False, "song_id": song_id, "error": str(exc)}


if __name__ == "__main__":
    try:
        import runpod
    except ImportError as exc:
        raise SystemExit(
            "runpod package missing. Install requirements-gpu.txt or run FastAPI via main.py",
        ) from exc
    runpod.serverless.start({"handler": handler})
