# OmniVoice Cloud API — Documentation

The OmniVoice Cloud API allows developers to perform zero-shot voice cloning and text-to-speech synthesis using reference audio samples.

---

## Base URL

- **Production Gateway**: `https://api.yourdomain.com`
- **Local Development**: `http://localhost:8000`

---

## Authentication

All API endpoints (except `/health` and `/api/token`) require authentication using one of the following methods:

1. **X-API-Key Header**:
   ```http
   X-API-Key: your_secret_api_key
   ```
2. **Bearer JWT Token**:
   ```http
   Authorization: Bearer <jwt_access_token>
   ```

---

## Endpoints Summary

### 1. Health Check

Checks system, Cloudflare R2 storage, and GPU inference status.

- **HTTP Method**: `GET`
- **Endpoint**: `/health`
- **Auth**: None required

#### Response `200 OK`
```json
{
  "gateway_status": "online",
  "service": "OmniVoice Cloud API Gateway",
  "timestamp": 1727500000.0,
  "storage": {
    "type": "Cloudflare R2",
    "bucket": "omnivoice-audio",
    "ready": true
  },
  "gpu_backend": {
    "status": "ready",
    "model": "k2-fsa/OmniVoice",
    "gpu": {
      "cuda_available": true,
      "device_name": "NVIDIA RTX 4090",
      "vram_allocated_mb": 4200.5,
      "vram_total_mb": 24576.0
    }
  }
}
```

---

### 2. Generate Access Token

Exchanges master API key for a JWT access token valid for 24 hours.

- **HTTP Method**: `POST`
- **Endpoint**: `/api/token`
- **Auth**: None

#### Request Body
```json
{
  "api_key": "your_secret_api_key"
}
```

#### Response `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1Ni...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

---

### 3. Upload Reference Audio Sample

Uploads target voice audio sample for zero-shot cloning. Audio is stored in Cloudflare R2 `reference/` and automatically deleted after 24 hours.

- **HTTP Method**: `POST`
- **Endpoint**: `/api/reference`
- **Auth**: `X-API-Key` or Bearer JWT
- **Content-Type**: `multipart/form-data`

#### Form Parameters
- `file`: Audio binary file (`.wav`, `.mp3`, `.flac`, `.ogg`). Max size: 25MB.

#### Response `200 OK`
```json
{
  "reference_id": "ref_a1b2c3d4e5f6",
  "object_key": "reference/ref_a1b2c3d4e5f6.wav",
  "presigned_url": "https://pub-xxx.r2.dev/reference/ref_a1b2c3d4e5f6.wav?expires=...",
  "retention_hours": 24
}
```

---

### 4. Synthesize Text-to-Speech (Voice Cloning)

Generates speech from text using OmniVoice and the provided voice reference.

- **HTTP Method**: `POST`
- **Endpoint**: `/api/tts`
- **Auth**: `X-API-Key` or Bearer JWT
- **Content-Type**: `application/json`

#### Request Body
```json
{
  "text": "Welcome to OmniVoice Cloud API. Voice cloning powered by RunPod GPU clusters.",
  "reference_id": "ref_a1b2c3d4e5f6",
  "prompt_text": "Optional transcript of reference audio for better clarity",
  "speed": 1.0,
  "temperature": 0.7
}
```

#### Response `200 OK`
```json
{
  "job_id": "job_9876543210ab",
  "status": "completed",
  "text": "Welcome to OmniVoice Cloud API...",
  "reference_id": "ref_a1b2c3d4e5f6",
  "download_url": "https://pub-xxx.r2.dev/generated/job_9876543210ab.wav?expires=...",
  "created_at": 1727500120.0,
  "duration_seconds": 3.42,
  "retention_hours": 24
}
```

---

### 5. Inspect Job Status

Retrieves the status and download link for a speech synthesis job.

- **HTTP Method**: `GET`
- **Endpoint**: `/api/job/{job_id}`
- **Auth**: `X-API-Key` or Bearer JWT

#### Response `200 OK`
```json
{
  "job_id": "job_9876543210ab",
  "status": "completed",
  "text": "Welcome to OmniVoice Cloud API...",
  "reference_id": "ref_a1b2c3d4e5f6",
  "download_url": "https://pub-xxx.r2.dev/generated/job_9876543210ab.wav?expires=...",
  "created_at": 1727500120.0,
  "duration_seconds": 3.42,
  "retention_hours": 24
}
```
