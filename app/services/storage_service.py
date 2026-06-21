import asyncio
import mimetypes
import re
import uuid

import boto3
import structlog
from botocore.exceptions import ClientError
from fastapi import UploadFile

from app.config import get_settings
from app.core.exceptions import ValidationError

logger = structlog.get_logger()

RESUME_EXTENSIONS = {"pdf", "doc", "docx"}
IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_RESUME_SIZE = 10 * 1024 * 1024
MAX_IMAGE_SIZE = 5 * 1024 * 1024


def _clean_filename(filename: str) -> str:
    name = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    return re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-") or "upload"


class StorageService:
    def __init__(self) -> None:
        self._client = None

    def _s3(self):
        if self._client is None:
            settings = get_settings()
            self._client = boto3.client("s3", region_name=settings.AWS_REGION)
        return self._client

    def _bucket(self) -> str:
        bucket = get_settings().S3_BUCKET_NAME
        if not bucket:
            raise ValidationError("S3 storage is not configured")
        return bucket

    async def upload_resume(self, file: UploadFile) -> tuple[str, str]:
        settings = get_settings()
        return await self._upload(
            file=file,
            prefix=settings.S3_RESUMES_PREFIX,
            allowed_extensions=RESUME_EXTENSIONS,
            max_size=MAX_RESUME_SIZE,
        )

    async def upload_profile_image(self, file: UploadFile) -> tuple[str, str]:
        settings = get_settings()
        return await self._upload(
            file=file,
            prefix=settings.S3_PROFILE_IMAGES_PREFIX,
            allowed_extensions=IMAGE_EXTENSIONS,
            max_size=MAX_IMAGE_SIZE,
        )

    async def _upload(
        self,
        *,
        file: UploadFile,
        prefix: str,
        allowed_extensions: set[str],
        max_size: int,
    ) -> tuple[str, str]:
        if not file.filename:
            raise ValidationError("No file provided")

        filename = _clean_filename(file.filename)
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in allowed_extensions:
            raise ValidationError(f"File type '{ext}' not allowed. Allowed: {', '.join(sorted(allowed_extensions))}")

        contents = await file.read()
        if len(contents) > max_size:
            raise ValidationError(f"File size exceeds {max_size // (1024 * 1024)} MB limit")

        key = f"{prefix.rstrip('/')}/{uuid.uuid4()}-{filename}"
        content_type = file.content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        bucket = self._bucket()

        await asyncio.to_thread(
            self._s3().put_object,
            Bucket=bucket,
            Key=key,
            Body=contents,
            ContentType=content_type,
            ServerSideEncryption="AES256",
        )
        logger.info("file_uploaded", bucket=bucket, key=key)
        return f"s3://{bucket}/{key}", key

    def get_download_url(self, value: str) -> str:
        if not value:
            return value
        if not value.startswith("s3://"):
            return value

        bucket, key = self._parse_s3_uri(value)
        settings = get_settings()
        try:
            return self._s3().generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=settings.S3_PRESIGNED_URL_EXPIRE_SECONDS,
            )
        except ClientError as exc:
            logger.error("presigned_url_failed", bucket=bucket, key=key, error=str(exc))
            raise ValidationError("Unable to generate file download URL") from exc

    async def delete_file(self, value: str) -> None:
        if not value or not value.startswith("s3://"):
            return
        bucket, key = self._parse_s3_uri(value)
        await asyncio.to_thread(self._s3().delete_object, Bucket=bucket, Key=key)
        logger.info("file_deleted", bucket=bucket, key=key)

    def _parse_s3_uri(self, value: str) -> tuple[str, str]:
        path = value.removeprefix("s3://")
        bucket, _, key = path.partition("/")
        if not bucket or not key:
            raise ValidationError("Invalid S3 object URI")
        return bucket, key


storage_service = StorageService()
