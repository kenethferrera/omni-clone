FROM pytorch/pytorch:2.4.0-cuda12.1-cudnn9-runtime

WORKDIR /app

# System dependencies for audio processing & git
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ffmpeg \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Environment settings for model caching & GPU
ENV MODEL_CACHE_DIR=/models/omnivoice
ENV TORCH_DTYPE=float16
ENV CUDA_VISIBLE_DEVICES=0
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Create model cache directory
RUN mkdir -p /models/omnivoice

# Install Python requirements and OmniVoice repository
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download HuggingFace model cache (optional step for fast cold start)
# RUN python3 -c "from huggingface_hub import snapshot_download; snapshot_download('k2-fsa/OmniVoice', local_dir='/models/omnivoice')"

# Copy application source code
COPY . /app/gpu_pod/

EXPOSE 8000

CMD ["python", "-m", "gpu_pod.serverless_handler"]
