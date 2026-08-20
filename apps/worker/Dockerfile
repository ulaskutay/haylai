FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIPELINE_MODE=gpu \
    DEMUCS_MODEL=htdemucs \
    BED_ML_ENABLED=true \
    BED_ENGINE=auto \
    BED_MAX_SECONDS=60 \
    ACESTEP_MODEL=ACE-Step/acestep-v15-xl-turbo-diffusers \
    ACESTEP_STEPS=8 \
    STABLE_AUDIO_MODEL=stabilityai/stable-audio-open-1.0 \
    STABLE_AUDIO_STEPS=100 \
    MUSICGEN_MODEL=facebook/musicgen-medium \
    BED_MODE=auto \
    HF_HOME=/app/.cache/huggingface \
    PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3.11-venv python3-pip ffmpeg libsndfile1 git \
    && rm -rf /var/lib/apt/lists/* \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

WORKDIR /app

COPY requirements.txt requirements-gpu.txt ./
RUN python3.11 -m pip install --no-cache-dir --upgrade pip \
    && python3.11 -m pip install --no-cache-dir \
        torch==2.5.1 torchaudio==2.5.1 \
        --index-url https://download.pytorch.org/whl/cu121 \
    && python3.11 -m pip install --no-cache-dir -r requirements-gpu.txt

RUN python3.11 - <<'PY'
import torch
from diffusers import AceStepPipeline
AceStepPipeline.from_pretrained("ACE-Step/acestep-v15-xl-turbo-diffusers", torch_dtype=torch.bfloat16)
print("acestep-turbo cached")
PY

COPY . .

CMD ["python3.11", "-u", "rp_handler.py"]
