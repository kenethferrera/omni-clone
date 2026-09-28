FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

WORKDIR /app

# Environment settings for model caching & GPU
ENV MODEL_CACHE_DIR=/models/omnivoice
ENV TORCH_DTYPE=float16
ENV CUDA_VISIBLE_DEVICES=0
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Create model cache directory
RUN mkdir -p /models/omnivoice

# Install Python requirements and OmniVoice repository
COPY gpu_pod/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . /app/gpu_pod/

EXPOSE 8000

CMD ["python", "-m", "gpu_pod.serverless_handler"]
