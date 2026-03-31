from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.core.enums import UserRole
from app.core.exceptions import ValidationError
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.profile import ProfileResponse, ProfileUpdateRequest, ResumeExtractResponse
from app.services.cloudinary_service import cloudinary_service
from app.services.profile_service import profile_service

router = APIRouter(prefix="/profile", tags=["Profile"])

ALLOWED_EXTENSIONS = {"pdf", "doc", "docx"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def _profile_response(profile, user: User) -> ProfileResponse:
    return ProfileResponse(
        id=str(profile.id),
        userId=str(profile.user_id),
        name=profile.name,
        email=profile.email,
        phone=profile.phone,
        role=profile.role,
        onboardingComplete=user.onboarding_complete,
        title=profile.title,
        location=profile.location,
        experience=profile.experience,
        preferredRole=profile.preferred_role,
        expectedSalary=profile.expected_salary,
        skills=profile.skills,
        education=profile.education,
        workExperience=profile.work_experience,
        certifications=profile.certifications,
        resumeUrl=profile.resume,
        bio=profile.bio,
        company=profile.company,
        companySize=profile.company_size,
        industry=profile.industry,
        website=profile.website,
        description=profile.description,
        founded=profile.founded,
        createdAt=profile.created_at.isoformat(),
        updatedAt=profile.updated_at.isoformat(),
    )


def _validate_file(file: UploadFile) -> str:
    if not file.filename:
        raise ValidationError("No file provided")
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")
    return ext


@router.get("/me", response_model=SuccessResponse[ProfileResponse])
async def get_my_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await profile_service.get_by_user_id(db, user.id)
    return SuccessResponse(data=_profile_response(profile, user))


@router.patch("/me", response_model=SuccessResponse[ProfileResponse])
async def update_my_profile(
    payload: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await profile_service.update(db, user, payload)
    return SuccessResponse(data=_profile_response(profile, user), message="Profile updated successfully")


@router.post("/resume", response_model=SuccessResponse[dict])
async def upload_resume(
    file: UploadFile,
    user: User = Depends(require_role(UserRole.JOB_SEEKER)),
    db: AsyncSession = Depends(get_db),
):
    _validate_file(file)
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise ValidationError("File size exceeds 5 MB limit")

    await file.seek(0)
    url, public_id = await cloudinary_service.upload_resume(file)
    await profile_service.update_resume(db, user.id, url, public_id)
    return SuccessResponse(data={"resumeUrl": url}, message="Resume uploaded successfully")


@router.post("/resume/extract", response_model=SuccessResponse[ResumeExtractResponse])
async def extract_resume(
    file: UploadFile,
    user: User = Depends(require_role(UserRole.JOB_SEEKER)),
    db: AsyncSession = Depends(get_db),
):
    """Upload resume, parse with Gemini OCR, and return structured fields."""
    ext = _validate_file(file)
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise ValidationError("File size exceeds 5 MB limit")

    # Upload to Cloudinary first
    await file.seek(0)
    url, public_id = await cloudinary_service.upload_resume(file)
    await profile_service.update_resume(db, user.id, url, public_id)

    # Parse with Gemini
    from app.agents.resume_agent import resume_agent

    parsed = await resume_agent.parse_resume(contents, ext)
    parsed["resumeUrl"] = url

    return SuccessResponse(data=ResumeExtractResponse(**parsed), message="Resume parsed successfully")
