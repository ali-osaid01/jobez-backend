import math
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.core.enums import UserRole
from app.db.session import get_db
from app.models.user import User
from app.schemas.application import (
    ApplicationApplyResponse,
    ApplicationCounts,
    ApplicationCreate,
    ApplicationListResponse,
    ApplicationResponse,
    ApplicationStatusUpdate,
)
from app.schemas.interview import InterviewResponse
from app.schemas.common import SuccessResponse
from app.services.application_service import INTERVIEW_MATCH_THRESHOLD, application_service
from app.services.storage_service import storage_service

router = APIRouter(prefix="/applications", tags=["Applications"])


def _app_response(app) -> ApplicationResponse:
    return ApplicationResponse(
        id=str(app.id),
        jobId=str(app.job_id),
        jobTitle=app.job_title,
        company=app.company,
        applicantId=str(app.applicant_id),
        applicantName=app.applicant_name,
        applicantEmail=app.applicant_email,
        status=app.status.value if hasattr(app.status, "value") else app.status,
        appliedDate=app.applied_date,
        resume=app.resume,
        coverLetter=app.cover_letter,
        matchScore=app.match_score,
        rejectionReason=app.rejection_reason,
        createdAt=app.created_at.isoformat(),
        updatedAt=app.updated_at.isoformat(),
    )


def _interview_response(interview) -> InterviewResponse:
    return InterviewResponse(
        id=str(interview.id),
        jobId=str(interview.job_id),
        applicationId=str(interview.application_id),
        jobTitle=interview.job_title,
        company=interview.company,
        applicantId=str(interview.applicant_id),
        applicantName=interview.applicant_name,
        scheduledDate=interview.scheduled_date,
        scheduledTime=interview.scheduled_time,
        duration=interview.duration,
        status=interview.status.value if hasattr(interview.status, "value") else interview.status,
        type=interview.type.value if hasattr(interview.type, "value") else interview.type,
        meetingLink=interview.meeting_link,
        notes=interview.notes,
        aiScore=interview.ai_score,
        aiSummary=interview.ai_summary,
        createdAt=interview.created_at.isoformat(),
        updatedAt=interview.updated_at.isoformat(),
    )


@router.get("", response_model=ApplicationListResponse)
async def list_applications(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = None,
    jobId: str | None = None,
    search: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    apps, total = await application_service.list_applications(
        db, user, page=page, limit=limit, status=status, job_id=jobId, search=search
    )
    raw = await application_service.get_status_counts(db, user, job_id=jobId, search=search)
    counts = ApplicationCounts(**raw)
    return ApplicationListResponse(
        data=[_app_response(a) for a in apps],
        total=total,
        page=page,
        limit=limit,
        total_pages=math.ceil(total / limit) if total > 0 else 0,
        counts=counts,
    )


@router.post("", status_code=201, response_model=SuccessResponse[ApplicationApplyResponse])
async def create_application(
    payload: ApplicationCreate,
    applicant: User = Depends(require_role(UserRole.JOB_SEEKER)),
    db: AsyncSession = Depends(get_db),
):
    app, interview = await application_service.create(db, applicant, payload)
    return SuccessResponse(
        data=ApplicationApplyResponse(
            application=_app_response(app),
            interview=_interview_response(interview) if interview else None,
            eligibleForInterview=interview is not None,
            interviewThreshold=INTERVIEW_MATCH_THRESHOLD,
        )
    )


@router.patch("/{app_id}/status", response_model=SuccessResponse[ApplicationResponse])
async def update_application_status(
    app_id: uuid.UUID,
    payload: ApplicationStatusUpdate,
    employer: User = Depends(require_role(UserRole.EMPLOYER)),
    db: AsyncSession = Depends(get_db),
):
    app = await application_service.update_status(db, app_id, employer.id, payload)
    return SuccessResponse(data=_app_response(app))


@router.get("/{app_id}/resume", response_model=SuccessResponse[dict])
async def get_resume(
    app_id: uuid.UUID,
    employer: User = Depends(require_role(UserRole.EMPLOYER)),
    db: AsyncSession = Depends(get_db),
):
    url = await application_service.get_resume_url(db, app_id, employer.id)
    return SuccessResponse(data={"url": storage_service.get_download_url(url)})


@router.post("/{app_id}/contact")
async def contact_applicant(
    app_id: uuid.UUID,
    employer: User = Depends(require_role(UserRole.EMPLOYER)),
    db: AsyncSession = Depends(get_db),
):
    await application_service.contact_applicant(db, app_id, employer.id)
    return {"message": "Contact request sent"}
