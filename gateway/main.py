import os
import uuid
import time
import logging
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from gateway.config import get_settings
from gateway.auth import verify_authentication, create_jwt_token
from gateway.r2_client import r2_storage
from gateway.runpod_client import runpod_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("omnivoice.gateway")

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version="2.1.0",
    description="Public API Gateway & Web Studio Interface for OmniVoice Voice Cloning Cloud Inference",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Web Studio UI
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
async def serve_web_interface():
    """Serve the Web Studio Interface at root route."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": settings.APP_NAME}


# Simple In-Memory Job Metadata Tracker
jobs_db = {}


# Request / Response Schemas
class TokenRequest(BaseModel):
    api_key: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=settings.MAX_TEXT_LENGTH, description="Text to synthesize")
    reference_id: Optional[str] = Field(None, description="Pre-uploaded reference audio ID")
    reference_audio_url: Optional[str] = Field(None, description="Direct URL to reference audio")
    prompt_text: Optional[str] = Field(None, description="Transcript of the reference audio for better zero-shot cloning")
    speed: float = Field(1.0, ge=0.5, le=2.0, description="Speech playback speed multiplier")
    temperature: float = Field(0.7, ge=0.1, le=1.5, description="Sampling temperature")


class TTSJobResponse(BaseModel):
    job_id: str
    status: str
    text: str
    reference_id: Optional[str]
    download_url: Optional[str]
    created_at: float
    duration_seconds: Optional[float] = None
    retention_hours: int = 24


class ReferenceUploadResponse(BaseModel):
    reference_id: str
    object_key: str
    presigned_url: str
    retention_hours: int = 24


@app.get("/health", tags=["Health"])
async def health_check():
    """System status and dependency health check."""
    runpod_health = await runpod_client.check_pod_health()
    r2_ready = r2_storage.is_configured()

    return {
        "gateway_status": "online",
        "service": settings.APP_NAME,
        "timestamp": time.time(),
        "storage": {
            "type": "Cloudflare R2",
            "bucket": settings.R2_BUCKET,
            "ready": r2_ready
        },
        "gpu_backend": runpod_health
    }


@app.post("/api/token", response_model=TokenResponse, tags=["Authentication"])
async def generate_token(req: TokenRequest):
    """Exchange valid API key for JWT bearer token."""
    if req.api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    token = create_jwt_token({"sub": "api_user"})
    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@app.post("/api/reference", response_model=ReferenceUploadResponse, tags=["Voice Cloning"])
async def upload_reference_audio(
    file: UploadFile = File(..., description="Audio sample file (.wav, .mp3) of target voice"),
    auth: dict = Depends(verify_authentication)
):
    """
    Upload a reference audio sample for voice cloning.
    Saves audio to Cloudflare R2 reference/ prefix.
    Returns reference_id to use in /api/tts calls.
    """
    if file.content_type not in settings.ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file MIME type '{file.content_type}'. Allowed: {settings.ALLOWED_MIME_TYPES}"
        )

    content = await file.read()
    if len(content) > settings.MAX_AUDIO_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Audio file exceeds maximum size limit of {settings.MAX_AUDIO_SIZE_MB}MB"
        )

    ref_id, object_key = r2_storage.upload_reference_audio(content, file.content_type or "audio/wav")
    signed_url = r2_storage.generate_presigned_download_url(object_key)

    return ReferenceUploadResponse(
        reference_id=ref_id,
        object_key=object_key,
        presigned_url=signed_url,
        retention_hours=settings.AUDIO_RETENTION_HOURS
    )


@app.post("/api/tts", response_model=TTSJobResponse, tags=["Voice Cloning"])
async def generate_text_to_speech(
    req: TTSRequest,
    auth: dict = Depends(verify_authentication)
):
    """
    Synthesize text into speech using OmniVoice zero-shot voice cloning.
    Requires either reference_id (uploaded via /api/reference) or reference_audio_url.
    Returns presigned download URL for generated audio.
    """
    if not req.reference_id and not req.reference_audio_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either 'reference_id' or 'reference_audio_url'."
        )

    job_id = f"job_{uuid.uuid4().hex[:12]}"
    start_time = time.time()

    # Determine reference audio location for RunPod worker
    ref_url = req.reference_audio_url
    if req.reference_id and not ref_url:
        ref_key = f"reference/{req.reference_id}.wav"
        ref_url = r2_storage.generate_presigned_download_url(ref_key, expires_in_seconds=3600)

    try:
        # Request inference from RunPod OmniVoice GPU worker
        audio_bytes = await runpod_client.generate_speech(
            text=req.text,
            reference_audio_url_or_base64=ref_url,
            prompt_text=req.prompt_text,
            speed=req.speed,
            temperature=req.temperature
        )

        # Upload output audio to Cloudflare R2 generated/ prefix
        object_key = r2_storage.upload_generated_audio(audio_bytes, job_id)
        download_url = r2_storage.generate_presigned_download_url(object_key, expires_in_seconds=86400)
        duration = round(time.time() - start_time, 2)

        job_data = {
            "job_id": job_id,
            "status": "completed",
            "text": req.text,
            "reference_id": req.reference_id,
            "download_url": download_url,
            "created_at": start_time,
            "duration_seconds": duration,
            "retention_hours": settings.AUDIO_RETENTION_HOURS
        }
        jobs_db[job_id] = job_data
        return TTSJobResponse(**job_data)

    except Exception as e:
        logger.error(f"TTS generation job failed [{job_id}]: {e}")
        jobs_db[job_id] = {
            "job_id": job_id,
            "status": "failed",
            "text": req.text,
            "reference_id": req.reference_id,
            "download_url": None,
            "created_at": start_time,
            "error": str(e)
        }
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Speech synthesis failed: {str(e)}"
        )


@app.get("/api/job/{job_id}", response_model=TTSJobResponse, tags=["Voice Cloning"])
async def get_job_status(job_id: str, auth: dict = Depends(verify_authentication)):
    """Fetch status and download link for a TTS job."""
    if job_id not in jobs_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found"
        )
    return TTSJobResponse(**jobs_db[job_id])
