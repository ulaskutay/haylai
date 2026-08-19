from __future__ import annotations

from pathlib import Path

from pipeline.audio import load_mono, to_mp3_bytes


def export_mp3(path: Path) -> bytes:
    audio, sr = load_mono(path)
    return to_mp3_bytes(audio, sr)
