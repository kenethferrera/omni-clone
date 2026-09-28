import base64
import httpx
import logging
from typing import Dict, Any, Optional
from gateway.config import get_settings

logger = logging.getLogger("omnivoice.runpod")
settings = get_settings()


class RunPodInferenceClient:
    """
    HTTP Client for sending inference jobs to either:
    1. RunPod Serverless Endpoints (https://api.runpod.ai/v2/{endpoint_id}/runsync) -> $0 cost when idle!
    2. Direct Pod HTTP URL (https://{pod_id}-8000.proxy.runpod.net)
    """

    def __init__(self):
        self.endpoint = settings.RUNPOD_API_ENDPOINT.rstrip('/')
        self.api_key = settings.RUNPOD_API_KEY
        self.timeout = settings.RUNPOD_TIMEOUT_SECONDS

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def is_serverless(self) -> bool:
        """Returns True if configured endpoint is a RunPod Serverless URL."""
        return "api.runpod.ai" in self.endpoint or "/v2/" in self.endpoint

    async def check_pod_health(self) -> Dict[str, Any]:
        """Check status and health of the OmniVoice GPU Pod or Serverless Endpoint."""
        if not self.endpoint:
            return {
                "status": "mock_mode",
                "message": "RUNPOD_API_ENDPOINT not configured.",
                "gpu_available": False
            }

        if self.is_serverless():
            # Query serverless endpoint health status
            health_url = f"{self.endpoint}/health"
            async with httpx.AsyncClient(timeout=10.0) as client:
                try:
                    resp = await client.get(health_url, headers=self._get_headers())
                    if resp.status_code == 200:
                        return {"type": "runpod_serverless", "status": "ready", "details": resp.json()}
                    return {"type": "runpod_serverless", "status": "active", "http_code": resp.status_code}
                except Exception as e:
                    return {"type": "runpod_serverless", "status": "active", "error": str(e)}

        # Direct Pod Health Check
        health_url = f"{self.endpoint}/health"
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(health_url, headers=self._get_headers())
                if response.status_code == 200:
                    return response.json()
                return {"type": "pod_proxy", "status": "unhealthy", "http_code": response.status_code}
            except Exception as e:
                return {"type": "pod_proxy", "status": "unreachable", "error": str(e)}

    async def generate_speech(
        self,
        text: str,
        reference_audio_url_or_base64: Optional[str] = None,
        prompt_text: Optional[str] = None,
        speed: float = 1.0,
        temperature: float = 0.7
    ) -> bytes:
        """
        Sends TTS voice cloning request to RunPod (Serverless or Direct Pod).
        Returns raw audio bytes (WAV format).
        """
        if not self.endpoint:
            raise ValueError("RUNPOD_API_ENDPOINT is not configured in environment settings.")

        # -------------------------------------------------------------
        # Path A: RunPod Serverless Endpoint (runsync)
        # -------------------------------------------------------------
        if self.is_serverless():
            runsync_url = self.endpoint
            if not runsync_url.endswith("/runsync"):
                runsync_url = f"{self.endpoint}/runsync"

            payload = {
                "input": {
                    "input_text": text,
                    "reference_audio": reference_audio_url_or_base64,
                    "prompt_text": prompt_text,
                    "speed": speed,
                    "temperature": temperature
                }
            }

            logger.info(f"Dispatching Serverless TTS job to {runsync_url}...")
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(runsync_url, json=payload, headers=self._get_headers())
                if resp.status_code != 200:
                    raise RuntimeError(f"Serverless request error ({resp.status_code}): {resp.text}")

                res_json = resp.json()
                if res_json.get("status") == "COMPLETED":
                    output = res_json.get("output", {})
                    if "audio_base64" in output:
                        return base64.b64decode(output["audio_base64"])
                    elif "error" in output:
                        raise RuntimeError(f"Serverless execution error: {output['error']}")
                raise RuntimeError(f"Serverless job did not complete cleanly: {res_json}")

        # -------------------------------------------------------------
        # Path B: Direct GPU Pod HTTP Proxy
        # -------------------------------------------------------------
        speech_url = f"{self.endpoint}/v1/audio/speech"
        payload = {
            "input_text": text,
            "reference_audio": reference_audio_url_or_base64,
            "prompt_text": prompt_text,
            "speed": speed,
            "temperature": temperature
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    speech_url,
                    json=payload,
                    headers=self._get_headers()
                )

                if response.status_code == 200:
                    return response.content
                else:
                    raise RuntimeError(f"OmniVoice GPU Pod error ({response.status_code}): {response.text}")
            except httpx.TimeoutException:
                raise TimeoutError("OmniVoice GPU inference timed out after 300 seconds.")
            except Exception as e:
                raise RuntimeError(f"Connection to RunPod GPU pod failed: {str(e)}")


runpod_client = RunPodInferenceClient()
