FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

WORKDIR /app

# Environment settings for model caching & GPU
ENV HF_HOME=/root/.cache/huggingface
ENV MODEL_CACHE_DIR=/models/omnivoice
ENV TORCH_DTYPE=float16
ENV CUDA_VISIBLE_DEVICES=0
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Create directories
RUN mkdir -p /models/omnivoice /root/.cache/huggingface

# Install Python requirements and OmniVoice repository
COPY gpu_pod/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Pre-bake model weights directly into the Docker image so cold start takes <5 seconds
# and workers NEVER download over network during inference!
RUN python -c "from huggingface_hub import snapshot_download; \
    print('Baking k2-fsa/OmniVoice into image...'); \
    snapshot_download('k2-fsa/OmniVoice'); \
    print('Baking higgs-audio-v2-tokenizer into image...'); \
    snapshot_download('eustlb/higgs-audio-v2-tokenizer'); \
    print('Baking whisper-large-v3-turbo into image...'); \
    snapshot_download('openai/whisper-large-v3-turbo'); \
    print('All weights pre-baked successfully!')"

# Copy application source code
COPY gpu_pod /app/gpu_pod
COPY OmniVoice /app/OmniVoice

EXPOSE 8000

CMD ["python", "-m", "gpu_pod.serverless_handler"]
