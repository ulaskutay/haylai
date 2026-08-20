# RunPod GitHub deploy uses the repository root as build context.
# Prefer this file in the UI (Dockerfile path: Dockerfile) if apps/worker/Dockerfile fails COPY.

FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIPELINE_MODE=gpu \
    DEMUCS_MODEL=htdemucs \
    PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3.11-venv python3-pip ffmpeg libsndfile1 git \
    && rm -rf /var/lib/apt/lists/* \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

WORKDIR /app

COPY apps/worker/requirements.txt apps/worker/requirements-gpu.txt ./
RUN python3.11 -m pip install --no-cache-dir --upgrade pip \
    && python3.11 -m pip install --no-cache-dir \
        torch==2.5.1 torchaudio==2.5.1 \
        --index-url https://download.pytorch.org/whl/cu121 \
    && python3.11 -m pip install --no-cache-dir -r requirements-gpu.txt

COPY apps/worker/ .
COPY rp_handler.py /app/rp_handler.py

CMD ["python3.11", "-u", "rp_handler.py"]
