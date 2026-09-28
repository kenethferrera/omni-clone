import os
import base64
import logging
import runpod
from gpu_pod.engine import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("omnivoice.serverless")

# Warm-load OmniVoice model into VRAM on worker initialization
logger.info("Initializing OmniVoice Serverless Worker & Loading Model into GPU Memory...")
engine.load_model()


def handler(job):
    """
    RunPod Serverless Handler for OmniVoice Zero-Shot Voice Cloning.
    Triggers on payload from https://api.runpod.ai/v2/{endpoint_id}/runsync
    """
    job_input = job.get("input", {})
    text = job_input.get("input_text") or job_input.get("text")
    reference_audio = job_input.get("reference_audio")
    prompt_text = job_input.get("prompt_text")
    speed = float(job_input.get("speed", 1.0))
    temperature = float(job_input.get("temperature", 0.7))

    if not text:
        return {"error": "Missing required field 'input_text' or 'text'."}

    # Fetch reference audio if URL or Base64
    ref_bytes = None
    if reference_audio:
        if reference_audio.startswith("http://") or reference_audio.startswith("https://"):
            import httpx
            try:
                resp = httpx.get(reference_audio, timeout=30.0)
                if resp.status_code == 200:
                    ref_bytes = resp.content
            except Exception as e:
                logger.error(f"Error fetching reference audio URL: {e}")
        elif "," in reference_audio:
            try:
                base64_data = reference_audio.split(",")[1]
                ref_bytes = base64.b64decode(base64_data)
            except Exception as e:
                logger.error(f"Error decoding base64 reference audio: {e}")
        else:
            try:
                ref_bytes = base64.b64decode(reference_audio)
            except Exception:
                pass

    try:
        audio_wav_bytes = engine.generate(
            text=text,
            reference_audio_bytes=ref_bytes,
            prompt_text=prompt_text,
            speed=speed,
            temperature=temperature
        )

        audio_b64 = base64.b64encode(audio_wav_bytes).decode("utf-8")
        return {
            "status": "completed",
            "format": "wav",
            "audio_base64": audio_b64
        }

    except Exception as e:
        logger.error(f"Serverless OmniVoice generation error: {e}")
        return {"error": str(e), "status": "failed"}


# Start RunPod Serverless worker loop
runpod.serverless.start({"handler": handler})
