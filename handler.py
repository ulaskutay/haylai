"""RunPod GitHub scanner looks at repo root for runpod.serverless.start()."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "apps" / "worker"))

from rp_handler import handler  # noqa: E402


if __name__ == "__main__":
    import runpod

    runpod.serverless.start({"handler": handler})
