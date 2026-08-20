from __future__ import annotations

import threading

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from pipeline.job import run_job
from pipeline.types import JobPayload

app = FastAPI(title="HAYL AI Audio Worker", version="0.1.0")


class JobRequest(BaseModel):
    song_id: str
    original_url: str
    instrumental_url: str
    upload_url: str
    genre: str = "pop"
    instruments: str = ""
    rhythm: str = "follow"
    bpm: float = 0
    callback_url: str = ""
    callback_secret: str = Field(default="")


@app.get("/")
@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "hayl-worker"}


def _run(payload: JobPayload) -> None:
    run_job(payload)


@app.post("/jobs")
def create_job(body: JobRequest) -> dict:
    payload = JobPayload.from_dict(body.model_dump())
    thread = threading.Thread(target=_run, args=(payload,), daemon=True)
    thread.start()
    return {"ok": True, "song_id": payload.song_id, "status": "accepted"}


@app.post("/jobs/sync")
def create_job_sync(body: JobRequest) -> dict:
    try:
        return run_job(JobPayload.from_dict(body.model_dump()))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
