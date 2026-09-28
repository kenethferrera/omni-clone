import httpx
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel, Field
from gpu_pod.engine import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("omnivoice.gpu_pod")

app = FastAPI(
    title="OmniVoice GPU Inference Worker",
    version="2.1.0",
    description="Dedicated GPU inference worker running inside RunPod container"
)


class SpeechRequest(BaseModel):
    input_text: str = Field(..., min_length=1, description="Text to synthesize")
    reference_audio: Optional[str] = Field(None, description="URL or base64 of reference audio sample")
    prompt_text: Optional[str] = Field(None, description="Transcript of reference audio")
    speed: float = Field(1.0, ge=0.5, le=2.0)
    temperature: float = Field(0.7, ge=0.1, le=1.5)


@app.on_event("startup")
def startup_event():
    """Warm load OmniVoice model into VRAM during container startup."""
    logger.info("Initializing OmniVoice GPU Pod Container...")
    engine.load_model()


@app.get("/health")
def health_check():
    """Health check endpoint for RunPod pod monitoring."""
    gpu_metrics = engine.get_gpu_info()
    return {
        "status": "ready" if engine.loaded else "loading",
        "model": engine.model_name,
        "model_loaded": engine.loaded,
        "gpu": gpu_metrics
    }


@app.post("/v1/audio/speech")
async def generate_speech(req: SpeechRequest):
    """
    Perform OmniVoice zero-shot voice cloning.
    Downloads reference audio if URL is passed, runs GPU synthesis, returns WAV stream.
    """
    ref_bytes = None
    if req.reference_audio:
        if req.reference_audio.startswith("http://") or req.reference_audio.startswith("https://"):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(req.reference_audio)
                    if resp.status_code == 200:
                        ref_bytes = resp.content
                    else:
                        logger.warning(f"Failed to fetch reference audio URL [{resp.status_code}]")
            except Exception as e:
                logger.error(f"Error fetching reference audio: {e}")
        elif "," in req.reference_audio:
            # Handle base64 encoded audio strings
            import base64
            try:
                base64_data = req.reference_audio.split(",")[1]
                ref_bytes = base64.b64decode(base64_data)
            except Exception as e:
                logger.error(f"Error decoding base64 reference audio: {e}")
        else:
            import base64
            try:
                ref_bytes = base64.b64decode(req.reference_audio)
            except Exception as e:
                logger.error(f"Error decoding raw base64 reference audio: {e}")

    try:
        audio_wav_bytes = engine.generate(
            text=req.input_text,
            reference_audio_bytes=ref_bytes,
            prompt_text=req.prompt_text,
            speed=req.speed,
            temperature=req.temperature
        )

        return Response(
            content=audio_wav_bytes,
            media_type="audio/wav",
            headers={"Content-Disposition": "attachment; filename=omnivoice_output.wav"}
        )
    except Exception as e:
        logger.error(f"GPU synthesis error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OmniVoice synthesis failure: {str(e)}"
        )
