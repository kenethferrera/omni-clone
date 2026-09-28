import os
import base64
import logging
import threading
import runpod
from gpu_pod.engine import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("omnivoice.serverless")

logger.info("OmniVoice Serverless Worker Initializing...")

# Pre-load OmniVoice and Whisper ASR models in a background daemon thread
# so that runpod.serverless.start() registers immediately without hitting startup timeouts!
def _background_model_preload():
    try:
        logger.info("Background pre-loading OmniVoice & Whisper ASR models into VRAM...")
        engine.load_model()
        logger.info("Models pre-loaded and ready for zero-latency inference!")
    except Exception as e:
        logger.error(f"Background model pre-load notice: {e}", exc_info=True)

preload_thread = threading.Thread(target=_background_model_preload, daemon=True)
preload_thread.start()


def handler(job):
    """
    RunPod Serverless Handler for OmniVoice Zero-Shot Voice Cloning & Voice Design.
    Triggers on payload from https://api.runpod.ai/v2/{endpoint_id}/runsync
    """
    job_input = job.get("input", {})
    action = job_input.get("action")
    if action == "ping":
        return {"status": "pong", "message": "OmniVoice worker active"}

    text = job_input.get("input_text") or job_input.get("text")
    reference_audio = job_input.get("reference_audio")
    prompt_text = job_input.get("prompt_text")
    instruct = job_input.get("instruct")
    language = job_input.get("language")
    num_step = int(job_input.get("num_step", 32))
    guidance_scale = float(job_input.get("guidance_scale", 2.0))
    denoise = bool(job_input.get("denoise", True))
    speed = float(job_input.get("speed", 1.0))
    duration = float(job_input["duration"]) if job_input.get("duration") is not None else None
    postprocess_output = bool(job_input.get("postprocess_output", True))

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
            instruct=instruct,
            language=language,
            num_step=num_step,
            guidance_scale=guidance_scale,
            denoise=denoise,
            speed=speed,
            duration=duration,
            postprocess_output=postprocess_output
        )

        audio_b64 = base64.b64encode(audio_wav_bytes).decode("utf-8")
        return {
            "status": "completed",
            "format": "wav",
            "audio_base64": audio_b64
        }

    except Exception as e:
        logger.error(f"Serverless OmniVoice generation error: {e}", exc_info=True)
        return {"error": str(e), "status": "failed"}


# Start RunPod Serverless worker loop immediately
logger.info("Registering with RunPod Serverless Daemon...")
runpod.serverless.start({"handler": handler})
