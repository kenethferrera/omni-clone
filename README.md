# AntiGravity — OmniVoice Cloud API

Production-ready standalone **OmniVoice Voice Cloning Cloud API** built with **FastAPI**, **Oracle Cloud VPS**, **RunPod PAYG GPUs**, and **Cloudflare R2 Object Storage**.

> Based on open-source zero-shot voice cloning model: [k2-fsa/OmniVoice](https://github.com/k2-fsa/OmniVoice.git)

---

## 🏗️ Architecture Blueprint

```
Client (Web / App / Script)
    │ HTTPS Request (with API Key / JWT)
    ▼
Oracle Cloud VPS (Gateway) ─── FastAPI + Nginx Reverse Proxy
    │
    ├─────► RunPod GPU Pod (PAYG RTX 4090 / 3090)
    │       └─► OmniVoice Model Inference (CUDA / PyTorch)
    │
    └─────► Cloudflare R2 Object Storage
            ├─► reference/  (Uploaded voice samples)
            └─► generated/  (Synthesized audio outputs - 24h retention)
```

---

## ✨ Features

- **Zero-Shot Voice Cloning**: Clone target voices using reference audio samples (`.wav`, `.mp3`).
- **Low Cost & High Efficiency**: Gateway stays online 24/7 on Oracle Always Free VPS, while GPU inference runs on Pay-As-You-Go RunPod pods.
- **24-Hour Expiration & Signed URLs**: Audio files stored temporarily in Cloudflare R2 with automatic lifecycle deletion after 24 hours.
- **Dual Authentication**: Access API via `X-API-Key` headers or JWT Bearer tokens.
- **Docker First Deployment**: Includes Dockerfiles for both Gateway service and RunPod GPU container.

---

## 📂 Repository Structure

```
omni clone/
├── plan.md                # Full Production Architecture & Roadmap
├── README.md              # Project Overview & Quick Start
├── docker-compose.yml     # Oracle Cloud Gateway Compose Stack
├── .env.example           # Environment Configuration Template
├── gateway/               # FastAPI API Gateway for Oracle Cloud
│   ├── Dockerfile
│   ├── main.py            # API Routes & Endpoints
│   ├── auth.py            # API Key & JWT Verification
│   ├── r2_client.py       # Cloudflare R2 S3 Storage Adapter
│   ├── runpod_client.py   # RunPod GPU Inference HTTP Client
│   ├── config.py          # App Settings & Environment Validation
│   └── requirements.txt
├── gpu_pod/               # OmniVoice GPU Worker for RunPod
│   ├── Dockerfile
│   ├── main.py            # Worker FastAPI Server
│   ├── engine.py          # OmniVoice PyTorch CUDA Inference Engine
│   └── requirements.txt
├── nginx/
│   └── nginx.conf         # Nginx Reverse Proxy Configuration
├── scripts/
│   └── test_api.py        # End-to-End Test Suite
└── docs/
    ├── api_docs.md        # REST API Documentation & Endpoints
    └── deployment_guide.md# Complete Cloud Deployment Instructions
```

---

## ⚡ Quick Start (Local Development)

### 1. Clone & Configure Environment

```bash
cp .env.example .env
```

### 2. Run API Gateway Locally

```bash
cd gateway
pip install -r requirements.txt
uvicorn gateway.main:app --reload --port 8000
```

Access Swagger UI interactive docs at `http://localhost:8000/docs`.

### 3. Run End-to-End Test Script

```bash
python3 scripts/test_api.py
```

---

## 📖 Documentation & Setup

- **[REST API Specifications](file:///c:/Users/Admin/omni%20clone/docs/api_docs.md)**
- **[Cloud Deployment Guide](file:///c:/Users/Admin/omni%20clone/docs/deployment_guide.md)**
- **[Full Production Architecture Plan](file:///c:/Users/Admin/omni%20clone/plan.md)**

---

## 📄 License

MIT License
