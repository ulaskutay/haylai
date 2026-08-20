from __future__ import annotations

from dataclasses import dataclass, field


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
    instruments: str = ""
    rhythm: str = "follow"
    bpm: float = 0.0
    extras: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "JobPayload":
        instruments = data.get("instruments") or ""
        if isinstance(instruments, list):
            instruments = ",".join(str(item) for item in instruments)
        try:
            bpm = float(data.get("bpm") or 0)
        except (TypeError, ValueError):
            bpm = 0.0
        return cls(
            song_id=data["song_id"],
            original_url=data["original_url"],
            instrumental_url=data.get("instrumental_url") or "",
            upload_url=data["upload_url"],
            genre=data.get("genre") or "pop",
            callback_url=data.get("callback_url") or "",
            callback_secret=data.get("callback_secret") or "",
            instruments=str(instruments),
            rhythm=str(data.get("rhythm") or "follow"),
            bpm=bpm,
        )
