FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIPELINE_MODE=gpu \
    DEMUCS_MODEL=htdemucs \
    PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3.11-venv python3-pip ffmpeg libsndfile1 git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements-gpu.txt ./
RUN python3.11 -m pip install --no-cache-dir --upgrade pip \
    && python3.11 -m pip install --no-cache-dir \
        torch==2.5.1 torchaudio==2.5.1 \
        --index-url https://download.pytorch.org/whl/cu121 \
    && python3.11 -m pip install --no-cache-dir -r requirements-gpu.txt

COPY . .

# Warm Demucs weights so cold start does not download on first job.
RUN python3.11 -c "from demucs.pretrained import get_model; get_model('htdemucs')"

# Licensed RVC .pth lives on a RunPod network volume, not in this image.
# RVC_MODEL_PATH=/runpod-volume/rvc/hayl.pth
# RVC_INFER_PY=/runpod-volume/rvc/infer.py
# RVC_INDEX_PATH=/runpod-volume/rvc/hayl.index

CMD ["python3.11", "-u", "rp_handler.py"]
