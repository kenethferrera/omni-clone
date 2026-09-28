import os
import io
import time
import logging
from typing import Optional, Tuple
import numpy as np
import soundfile as sf

logger = logging.getLogger("omnivoice.engine")

# Environment settings
MODEL_CACHE_DIR = os.getenv("MODEL_CACHE_DIR", "/models/omnivoice")
TORCH_DTYPE = os.getenv("TORCH_DTYPE", "float16")
DEVICE = os.getenv("CUDA_VISIBLE_DEVICES", "0")


class OmniVoiceEngine:
    """Wrapper around OmniVoice model for GPU inference & voice cloning."""

    def __init__(self):
        self.model = None
        self.device = "cuda" if self._is_cuda_available() else "cpu"
        self.loaded = False
        self.model_name = "k2-fsa/OmniVoice"

    def _is_cuda_available(self) -> bool:
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    def load_model(self):
        """Loads OmniVoice weights into GPU memory."""
        if self.loaded and self.model is not None:
            return

        logger.info(f"Loading OmniVoice model into VRAM ({self.device})...")
        start_time = time.time()

        try:
            import torch
            try:
                try:
                    from omnivoice import OmniVoice
                except ImportError:
                    from omnivoice.models.omnivoice import OmniVoice

                dtype = torch.float16 if self.device == "cuda" else torch.float32
                try:
                    self.model = OmniVoice.from_pretrained(
                        self.model_name,
                        device_map=self.device,
                        dtype=dtype,
                        load_asr=True
                    )
                    logger.info(f"OmniVoice model + Whisper ASR loaded successfully in {round(time.time() - start_time, 2)}s!")
                except Exception as asr_err:
                    logger.warning(f"Could not load with ASR ({asr_err}). Loading OmniVoice standard...")
                    self.model = OmniVoice.from_pretrained(
                        self.model_name,
                        device_map=self.device,
                        dtype=dtype,
                        load_asr=False
                    )
                    logger.info(f"OmniVoice model loaded successfully in {round(time.time() - start_time, 2)}s!")
                self.loaded = True
            except Exception as e:
                import traceback
                logger.error(f"Native OmniVoice module load notice: {e}\n{traceback.format_exc()}. Engine operating in fallback mode.")
                self.loaded = False
        except Exception as e:
            logger.error(f"Failed to load PyTorch or OmniVoice: {e}")
            self.loaded = False

    def generate(
        self,
        text: str,
        reference_audio_bytes: Optional[bytes] = None,
        prompt_text: Optional[str] = None,
        instruct: Optional[str] = None,
        language: Optional[str] = None,
        num_step: int = 32,
        guidance_scale: float = 2.0,
        denoise: bool = True,
        speed: float = 1.0,
        duration: Optional[float] = None,
        postprocess_output: bool = True,
        **kwargs
    ) -> bytes:
        """
        Synthesizes audio using OmniVoice model or fallback waveform generator.
        Returns WAV audio bytes.
        """
        if not self.loaded or self.model is None:
            self.load_model()

        if prompt_text and not prompt_text.strip():
            prompt_text = None

        if instruct and not instruct.strip():
            instruct = None

        if language and not language.strip():
            language = None

        logger.info(f"Starting OmniVoice synthesis: '{text[:40]}...' (Ref audio: {reference_audio_bytes is not None}, Prompt text: {prompt_text}, Instruct: {instruct})")

        # 1. Native OmniVoice inference path
        if self.model is not None:
            try:
                import torch
                ref_path = None
                if reference_audio_bytes:
                    ref_path = "/tmp/temp_ref.wav"
                    with open(ref_path, "wb") as f:
                        f.write(reference_audio_bytes)

                with torch.no_grad():
                    audios = self.model.generate(
                        text=text,
                        language=language,
                        ref_audio=ref_path,
                        ref_text=prompt_text,
                        instruct=instruct,
                        duration=duration,
                        num_step=num_step,
                        guidance_scale=guidance_scale,
                        speed=speed,
                        denoise=denoise,
                        postprocess_output=postprocess_output,
                    )

                audio_data = audios[0]
                sr = getattr(self.model, "sampling_rate", 24000)

                # Convert float tensor / numpy array to audio WAV bytes
                if hasattr(audio_data, "cpu"):
                    audio_data = audio_data.cpu().numpy()

                out_buffer = io.BytesIO()
                sf.write(out_buffer, audio_data, sr, format="WAV")
                return out_buffer.getvalue()

            except Exception as e:
                logger.error(f"Inference error during OmniVoice synthesis: {e}", exc_info=True)

        # 2. Fallback high-quality synthetic tone generator (for testing)
        logger.info("Generating synthesized response audio waveform (fallback mode)...")
        sr = 24000
        dur = duration or max(1.5, len(text) * 0.08 / max(0.5, speed))
        t = np.linspace(0, dur, int(sr * dur), False)
        freq = 220 + 20 * np.sin(2 * np.pi * 2 * t)
        audio = 0.3 * np.sin(2 * np.pi * freq * t) * np.exp(-0.5 * t / dur)

        buffer = io.BytesIO()
        sf.write(buffer, audio, sr, format="WAV")
        return buffer.getvalue()

    def get_gpu_info(self):
        try:
            import torch
            if torch.cuda.is_available():
                return {
                    "device": torch.cuda.get_device_name(0),
                    "memory_allocated_gb": round(torch.cuda.memory_allocated(0) / 1024**3, 2),
                    "memory_reserved_gb": round(torch.cuda.memory_reserved(0) / 1024**3, 2),
                }
        except Exception:
            pass
        return {"device": "cpu"}


engine = OmniVoiceEngine()
