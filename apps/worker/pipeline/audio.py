from __future__ import annotations

import io
import os
import subprocess
import tempfile
from pathlib import Path

import httpx
import numpy as np
import soundfile as sf


def ffmpeg_bin() -> str:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def to_wav(src: Path, dest: Path | None = None, sr: int = 44100) -> Path:
    dest = dest or src.with_suffix(".wav")
    try:
        audio, file_sr = sf.read(str(src), always_2d=False)
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        if file_sr != sr:
            audio = resample(audio.astype(np.float32), file_sr, sr)
        write_wav(dest, audio.astype(np.float32), sr)
        return dest
    except Exception:
        pass
    subprocess.run(
        [
            ffmpeg_bin(),
            "-y",
            "-i",
            str(src),
            "-ac",
            "1",
            "-ar",
            str(sr),
            str(dest),
        ],
        check=True,
        capture_output=True,
    )
    return dest


def storage_root() -> Path:
    env = os.environ.get("STORAGE_ROOT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[3] / "data" / "audio"


def _local_path(url: str) -> Path | None:
    if not url.startswith("local://"):
        return None
    rel = url.removeprefix("local://").lstrip("/")
    path = (storage_root() / rel).resolve()
    root = storage_root().resolve()
    if root not in path.parents and path != root:
        raise RuntimeError("Invalid local storage path")
    return path


def _public_headers(url: str, extra: dict | None = None) -> dict[str, str]:
    headers = dict(extra or {})
    headers.setdefault("User-Agent", "HaylWorker/1.0")
    if "ngrok" in url:
        headers["ngrok-skip-browser-warning"] = "1"
    return headers


def download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = (url or "").strip()
    if not url:
        raise RuntimeError("empty download url")
    if not url.startswith(("http://", "https://", "local://")):
        raise RuntimeError(f"invalid download url: {url[:80]!r}")
    local = _local_path(url)
    if local:
        dest.write_bytes(local.read_bytes())
        return dest
    with httpx.Client(timeout=120, follow_redirects=True) as client:
        res = client.get(url, headers=_public_headers(url))
        res.raise_for_status()
        dest.write_bytes(res.content)
    return dest


def upload_bytes(url: str, data: bytes, content_type: str = "audio/mpeg") -> None:
    url = (url or "").strip()
    if not url:
        raise RuntimeError("empty upload url")
    if not url.startswith(("http://", "https://", "local://")):
        raise RuntimeError(f"invalid upload url: {url[:80]!r}")
    local = _local_path(url)
    if local:
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_bytes(data)
        return
    with httpx.Client(timeout=120) as client:
        res = client.put(
            url,
            content=data,
            headers=_public_headers(url, {"Content-Type": content_type}),
        )
        res.raise_for_status()


def load_mono(path: Path, sr: int = 44100) -> tuple[np.ndarray, int]:
    audio, file_sr = sf.read(str(path), always_2d=False)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if file_sr != sr:
        audio = resample(audio, file_sr, sr)
        file_sr = sr
    return audio.astype(np.float32), file_sr


def resample(x: np.ndarray, orig: int, target: int) -> np.ndarray:
    if orig == target:
        return x
    n = int(round(len(x) * target / orig))
    xp = np.linspace(0.0, 1.0, num=len(x), endpoint=False)
    xq = np.linspace(0.0, 1.0, num=n, endpoint=False)
    return np.interp(xq, xp, x).astype(np.float32)


def write_wav(path: Path, audio: np.ndarray, sr: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), audio, sr)
    return path


def to_mp3_bytes(audio: np.ndarray, sr: int) -> bytes:
    with tempfile.TemporaryDirectory() as tmp:
        wav_path = Path(tmp) / "master.wav"
        mp3_path = Path(tmp) / "master.mp3"
        write_wav(wav_path, audio, sr)
        try:
            subprocess.run(
                [
                    ffmpeg_bin(),
                    "-y",
                    "-i",
                    str(wav_path),
                    "-codec:a",
                    "libmp3lame",
                    "-b:a",
                    "320k",
                    str(mp3_path),
                ],
                check=True,
                capture_output=True,
            )
            return mp3_path.read_bytes()
        except (subprocess.CalledProcessError, FileNotFoundError):
            buf = io.BytesIO()
            sf.write(buf, audio, sr, format="WAV")
            return buf.getvalue()


def pipeline_mode() -> str:
    return os.environ.get("PIPELINE_MODE", "cpu").lower()


def use_gpu_models() -> bool:
    mode = pipeline_mode()
    if mode in {"gpu", "real", "runpod"}:
        return True
    if mode == "auto":
        try:
            import torch

            return bool(torch.cuda.is_available())
        except Exception:
            return False
    return False
