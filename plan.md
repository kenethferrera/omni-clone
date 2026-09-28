# AntiGravity — OmniVoice Cloud API (PLAN)

> Production roadmap for deploying **OmniVoice Voice Cloning** as a standalone cloud API using **Oracle Cloud**, **RunPod Pods (PAYG)**, and **Cloudflare R2**.

**Version:** 2.1  
**Status:** Production Planning

---

# Project Vision

Build a secure, scalable, low-cost **OmniVoice Voice Cloning API** where:

- Oracle Cloud acts as the public API gateway.
- RunPod Pods provide GPU inference.
- OmniVoice runs entirely inside the GPU pod.
- Cloudflare R2 stores temporary audio files for 24 hours.
- The API is reusable by any frontend, mobile app, automation, or backend.

---

# Goals

## Functional Goals

- Voice cloning using a reference audio sample.
- Text-to-speech generation using OmniVoice.
- REST API for inference.
- Temporary storage for generated audio.
- Signed URL delivery for audio downloads.

## Non-Functional Goals

- Optimized for **16 GB VRAM GPUs**.
- GPU scales to zero when idle.
- Oracle server remains online 24/7.
- Automatic deletion of user audio after 24 hours.
- Docker-first deployment.

---

# Final Architecture

Client
    │ HTTPS
    ▼
Oracle Cloud VPS
(FastAPI API Gateway)
    │
    ▼
RunPod Pod (PAYG GPU)
(OmniVoice + CUDA + FastAPI)
    │
    ▼
Cloudflare R2
(Temporary Audio Storage)

**Important:** Oracle never stores or serves OmniVoice model weights.

---

# Technology Stack

| Layer | Technology |
|--------|------------|
| API Gateway | FastAPI |
| GPU Backend | RunPod Pods (PAYG) |
| Voice Model | OmniVoice |
| Object Storage | Cloudflare R2 |
| Reverse Proxy | Nginx |
| Runtime | Docker + Docker Compose |
| Authentication | JWT + API Key |
| Database | SQLite (default) / PostgreSQL (optional) |

---

# Model Storage Strategy

## OmniVoice Model Location

The OmniVoice model MUST live inside the RunPod Pod.

### Storage Location

/models/omnivoice/

### Contents

- model weights
- tokenizer
- configuration
- inference assets

### Rules

- Download once during Docker image build **or** first pod startup.
- Cache model on RunPod pod disk.
- Load model once during container startup.
- Keep model in GPU memory while pod is running.

### Never Store Model In

- Oracle Cloud storage.
- Cloudflare R2.
- Client devices.

---

# Storage Strategy

## Oracle Cloud

Stores only:

- API configuration.
- Authentication secrets.
- Job metadata.
- Request logs (optional).

Never stores generated audio permanently.

## Cloudflare R2

Bucket layout:

generated/
reference/

### Retention

| Folder | Retention |
|--------|-----------|
| generated/ | 24 Hours |
| reference/ | 24 Hours |

Lifecycle rules delete objects automatically after one day.

---

# Development Phases

## Phase 1 — Infrastructure

### Objective

Provision cloud infrastructure.

### Deliverables

- Oracle Cloud VM.
- Docker installed.
- HTTPS reverse proxy.
- Cloudflare R2 bucket.
- RunPod Pod template.

### Checklist

- [ ] Oracle VM ready.
- [ ] Docker installed.
- [ ] Docker Compose installed.
- [ ] Nginx configured.
- [ ] HTTPS configured.
- [ ] Cloudflare R2 bucket created.
- [ ] Lifecycle rules enabled.
- [ ] RunPod account configured.
- [ ] PAYG Pod template created.

---

## Phase 2 — OmniVoice GPU Service

### Objective

Deploy OmniVoice inside RunPod.

### Deliverables

- Production Docker image.
- OmniVoice API service.
- Health endpoint.
- Warm model loading.

### Checklist

- [ ] CUDA runtime installed.
- [ ] PyTorch installed.
- [ ] OmniVoice installed.
- [ ] Model downloaded to `/models`.
- [ ] Model cached.
- [ ] Startup warmup completed.
- [ ] `/health` endpoint.
- [ ] `/v1/audio/speech` endpoint.

### Performance Targets

| Metric | Target |
|--------|--------|
| Cold startup | 20–35 seconds |
| Warm inference | 2–8 seconds |
| 5-minute narration | 15–30 seconds |

---

## Phase 3 — Oracle FastAPI Gateway

### Objective

Expose a secure public API.

### Endpoints

| Method | Endpoint |
|--------|----------|
| GET | `/health` |
| POST | `/api/reference` |
| POST | `/api/tts` |
| GET | `/api/job/{id}` |

### Responsibilities

- Authentication.
- Request validation.
- Upload reference audio.
- Call RunPod inference endpoint.
- Upload generated audio to R2.
- Return signed URL.

### Checklist

- [ ] JWT authentication.
- [ ] API key middleware.
- [ ] Input validation.
- [ ] Audio validation.
- [ ] Request timeout handling.
- [ ] Signed URL response.

---

## Phase 4 — Cloudflare R2 Integration

### Objective

Temporary object storage.

### Responsibilities

- Upload generated audio.
- Upload reference audio.
- Generate signed URLs.
- Automatic expiration after 24 hours.

### Checklist

- [ ] Bucket created.
- [ ] Upload utility.
- [ ] Download utility.
- [ ] Signed URL generation.
- [ ] Lifecycle expiration.
- [ ] Cleanup verification.

---

## Phase 5 — Security Hardening

### Objective

Production-ready security.

### Checklist

- [ ] HTTPS only.
- [ ] CORS whitelist.
- [ ] JWT verification.
- [ ] API key verification.
- [ ] MIME validation.
- [ ] Audio duration limits.
- [ ] Upload size limits.
- [ ] SSRF protection.
- [ ] Secret management with `.env`.

---

## Phase 6 — Monitoring & Logging

### Objective

Monitor API health and GPU status.

### Metrics

- Request count.
- Success rate.
- Failure rate.
- Generation duration.
- GPU memory usage.
- GPU utilization.
- Cold starts.

### Checklist

- [ ] Structured logs.
- [ ] Health metrics endpoint.
- [ ] GPU metrics endpoint.
- [ ] Error logging.

---

## Phase 7 — Cost Optimization

### RunPod

- PAYG Pods only.
- One GPU per pod.
- Auto-start pod on demand.
- Auto-stop after idle timeout.
- Single inference concurrency.

### Cloudflare R2

- Standard Storage.
- 24-hour lifecycle rules.
- Signed URLs expire in 15–30 minutes.

### Oracle Cloud

- Always Free resources only.
- Lightweight FastAPI gateway.
- No GPU workloads.

---

# Environment Variables

## Oracle Cloud

RUNPOD_API_KEY=
RUNPOD_POD_ID=
RUNPOD_API_ENDPOINT=

R2_ENDPOINT=
R2_BUCKET=
R2_ACCESS_KEY=
R2_SECRET_KEY=
R2_REGION=

JWT_SECRET=
API_KEY=

AUDIO_RETENTION_HOURS=24
REFERENCE_RETENTION_HOURS=24

CORS_ORIGINS=

## RunPod Pod

MODEL_CACHE_DIR=/models/omnivoice
CUDA_VISIBLE_DEVICES=0
TORCH_DTYPE=float16
MAX_CONCURRENT_REQUESTS=1

---

# Testing Checklist

## API

- [ ] Health endpoint.
- [ ] Authentication.
- [ ] Invalid request handling.
- [ ] Voice cloning request.
- [ ] Timeout handling.

## GPU

- [ ] Pod startup.
- [ ] Model warm load.
- [ ] Warm inference.
- [ ] CUDA OOM handling.
- [ ] Graceful shutdown.

## Storage

- [ ] Upload reference audio.
- [ ] Upload generated audio.
- [ ] Signed URL generation.
- [ ] URL expiration.
- [ ] Lifecycle deletion.

---

# Milestones

| Milestone | Status |
|-----------|--------|
| Infrastructure Ready | ☑ Completed |
| RunPod OmniVoice API | ☑ Completed |
| Oracle API Gateway | ☑ Completed |
| Cloudflare R2 Integration | ☑ Completed |
| Security Hardening | ☑ Completed |
| Monitoring & Logging | ☑ Completed |
| Production Deployment Package | ☑ Completed |

---

# Deliverables

- Production Docker image for OmniVoice.
- Oracle FastAPI Gateway.
- RunPod Pod deployment package.
- Cloudflare R2 integration.
- Nginx configuration.
- Environment templates.
- API documentation.
- Deployment guide.
- Cost guide.
- Troubleshooting guide.

---

# Project Scope

## Included

- OmniVoice voice cloning.
- REST API.
- Oracle Cloud deployment.
- RunPod Pods deployment.
- Cloudflare R2 storage.
- Docker deployment.
- Authentication.
- Monitoring and cleanup.
