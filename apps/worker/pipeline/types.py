from __future__ import annotations

from dataclasses import dataclass


STEPS = ("analyzing", "cleaning", "pitch", "rvc", "mix", "export")


@dataclass
class JobPayload:
    song_id: str
    original_url: str
    instrumental_url: str
    upload_url: str
    genre: str
    callback_url: str
    callback_secret: str

    @classmethod
    def from_dict(cls, data: dict) -> "JobPayload":
        return cls(
            song_id=data["song_id"],
            original_url=data["original_url"],
            instrumental_url=data["instrumental_url"],
            upload_url=data["upload_url"],
            genre=data.get("genre") or "pop",
            callback_url=data.get("callback_url") or "",
            callback_secret=data.get("callback_secret") or "",
        )
