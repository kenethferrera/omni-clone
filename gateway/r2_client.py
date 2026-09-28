import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from gateway.config import get_settings
import logging
import uuid
from typing import Tuple, Optional

logger = logging.getLogger("omnivoice.r2")
settings = get_settings()


class R2StorageClient:
    """Cloudflare R2 Object Storage Manager via S3 API."""

    def __init__(self):
        self.bucket = settings.R2_BUCKET
        self.s3_client = None

        if settings.R2_ENDPOINT and settings.R2_ACCESS_KEY and settings.R2_SECRET_KEY:
            try:
                self.s3_client = boto3.client(
                    "s3",
                    endpoint_url=settings.R2_ENDPOINT,
                    aws_access_key_id=settings.R2_ACCESS_KEY,
                    aws_secret_access_key=settings.R2_SECRET_KEY,
                    region_name=settings.R2_REGION,
                    config=Config(signature_version="s3v4")
                )
            except Exception as e:
                logger.error(f"Failed to initialize S3 client for Cloudflare R2: {e}")
        else:
            logger.warning("Cloudflare R2 settings missing. Running in mock/local fallback mode.")

    def is_configured(self) -> bool:
        return self.s3_client is not None

    def upload_reference_audio(self, file_bytes: bytes, content_type: str = "audio/wav") -> Tuple[str, str]:
        """
        Uploads reference audio sample to reference/ key in R2.
        Returns (reference_id, object_key).
        """
        ref_id = f"ref_{uuid.uuid4().hex[:12]}"
        object_key = f"reference/{ref_id}.wav"

        if not self.s3_client:
            # Fallback mock for testing environment
            return ref_id, object_key

        try:
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=object_key,
                Body=file_bytes,
                ContentType=content_type
            )
            return ref_id, object_key
        except (BotoCoreError, ClientError) as e:
            logger.error(f"R2 upload reference error: {e}")
            raise RuntimeError(f"Failed to upload reference audio to storage: {str(e)}")

    def upload_generated_audio(self, audio_bytes: bytes, job_id: str, content_type: str = "audio/wav") -> str:
        """
        Uploads synthesized output audio to generated/ key in R2.
        Returns object_key.
        """
        object_key = f"generated/{job_id}.wav"

        if not self.s3_client:
            return object_key

        try:
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=object_key,
                Body=audio_bytes,
                ContentType=content_type
            )
            return object_key
        except (BotoCoreError, ClientError) as e:
            logger.error(f"R2 upload generated audio error: {e}")
            raise RuntimeError(f"Failed to upload generated audio to storage: {str(e)}")

    def generate_presigned_download_url(self, object_key: str, expires_in_seconds: int = 86400) -> str:
        """
        Generates a 24-hour presigned URL for downloading reference or generated audio.
        """
        if settings.R2_PUBLIC_URL_PREFIX:
            return f"{settings.R2_PUBLIC_URL_PREFIX.rstrip('/')}/{object_key}"

        if not self.s3_client:
            return f"https://mock-r2.local/{self.bucket}/{object_key}?expires={expires_in_seconds}"

        try:
            url = self.s3_client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self.bucket, "Key": object_key},
                ExpiresIn=expires_in_seconds
            )
            return url
        except (BotoCoreError, ClientError) as e:
            logger.error(f"R2 presigned URL error: {e}")
            return f"https://r2.storage/{object_key}"

    def get_audio_file(self, object_key: str) -> Optional[bytes]:
        """Retrieves raw audio bytes from R2 object key."""
        if not self.s3_client:
            return None

        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=object_key)
            return response["Body"].read()
        except Exception as e:
            logger.error(f"Failed to fetch object {object_key} from R2: {e}")
            return None


r2_storage = R2StorageClient()
