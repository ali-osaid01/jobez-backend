import cloudinary
import cloudinary.uploader
import structlog
from fastapi import UploadFile

from app.config import get_settings
from app.core.exceptions import ValidationError

logger = structlog.get_logger()

ALLOWED_EXTENSIONS = {"pdf", "doc", "docx"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


class CloudinaryService:
    def __init__(self):
        self._configured = False

    def _ensure_configured(self):
        settings = get_settings()
        if not settings.CLOUDINARY_CLOUD_NAME:
            raise ValidationError("Cloudinary is not configured")
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
        )
        self._configured = True

    async def upload_resume(self, file: UploadFile) -> tuple[str, str]:
        if not file.filename:
            raise ValidationError("No file provided")
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            raise ValidationError(f"File type '{ext}' not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise ValidationError("File size exceeds 10 MB limit")
        self._ensure_configured()
        result = cloudinary.uploader.upload(
            contents,
            resource_type="raw",
            folder="jobez/resumes",
            format=ext,
        )
        logger.info("resume_uploaded", public_id=result["public_id"])
        return result["secure_url"], result["public_id"]

    async def delete_file(self, public_id: str) -> None:
        self._ensure_configured()
        cloudinary.uploader.destroy(public_id, resource_type="raw")
        logger.info("file_deleted", public_id=public_id)


cloudinary_service = CloudinaryService()