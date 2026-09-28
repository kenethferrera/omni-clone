#!/bin/bash

echo "=========================================="
echo "Installing OmniVoice on RunPod Container"
echo "=========================================="

# 1. Update system & dependencies
apt-get update && apt-get install -y ffmpeg libsndfile1 git curl

# 2. Install Python requirements & OmniVoice
pip install --no-cache-dir fastapi uvicorn soundfile librosa scipy numpy huggingface-hub httpx pydantic
pip install --no-cache-dir git+https://github.com/k2-fsa/OmniVoice.git

# 3. Create model directory
mkdir -p /models/omnivoice

# 4. Clone omni clone repository or pull code
cd /workspace
git clone https://github.com/k2-fsa/OmniVoice.git || true

echo "Setup complete! Starting OmniVoice GPU Worker on port 8000..."
python3 -m uvicorn gpu_pod.main:app --host 0.0.0.0 --port 8000
