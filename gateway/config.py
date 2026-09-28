from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    # API Gateway Config
    APP_NAME: str = "OmniVoice Cloud API Gateway"
    API_V1_PREFIX: str = "/api"
    DEBUG: bool = False

    # Security & Auth
    API_KEY: str = "default_secure_api_key_change_in_production"
    JWT_SECRET: str = "default_jwt_secret_key_change_in_production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    # RunPod Pod Configuration
    RUNPOD_API_KEY: str = ""
    RUNPOD_POD_ID: str = ""
    RUNPOD_API_ENDPOINT: str = ""  # Direct Pod HTTP URL e.g. https://xxx-8000.proxy.runpod.net or Serverless URL
    RUNPOD_TIMEOUT_SECONDS: int = 300

    # Cloudflare R2 Storage Configuration
    R2_ENDPOINT: str = ""  # e.g., https://<account_id>.r2.cloudflarestorage.com
    R2_BUCKET: str = "omnivoice-audio"
    R2_ACCESS_KEY: str = ""
    R2_SECRET_KEY: str = ""
    R2_REGION: str = "auto"
    R2_PUBLIC_URL_PREFIX: str = ""  # Optional custom domain or R2 public dev URL

    # Audio Limits & Retention
    AUDIO_RETENTION_HOURS: int = 24
    MAX_AUDIO_SIZE_MB: int = 25
    MAX_TEXT_LENGTH: int = 5000
    ALLOWED_MIME_TYPES: List[str] = [
        "audio/wav",
        "audio/x-wav",
        "audio/mpeg",
        "audio/mp3",
        "audio/ogg",
        "audio/flac"
    ]

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
