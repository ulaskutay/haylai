from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from pipeline.audio import load_mono, write_wav


def _run_rvc_cli(path: Path, dest: Path) -> Path:
    model = os.environ.get("RVC_MODEL_PATH", "")
    infer = os.environ.get("RVC_INFER_PY", "")
    if not model or not Path(model).exists():
        raise RuntimeError("RVC model is not configured")
    if infer and Path(infer).exists():
        cmd = [
            sys.executable,
            infer,
            "--input",
            str(path),
            "--output",
            str(dest),
            "--model",
            model,
        ]
        index = os.environ.get("RVC_INDEX_PATH", "")
        if index:
            cmd.extend(["--index", index])
        subprocess.run(cmd, check=True)
        if not dest.exists():
            raise RuntimeError("RVC infer produced no output")
        return dest
    raise RuntimeError("RVC_INFER_PY is not set")


def convert(path: Path, workdir: Path) -> Path:
    dest = workdir / "rvc.wav"
    try:
        return _run_rvc_cli(path, dest)
    except Exception:
        pass
    audio, sr = load_mono(path)
    write_wav(dest, audio, sr)
    return dest
