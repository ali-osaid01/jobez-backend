import math
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.core.enums import UserRole
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.schemas.interview import (
    AIInterviewResult,
    AIInterviewStartResponse,
    InterviewCreate,
    InterviewResponse,
    InterviewResponsesRequest,
    InterviewUpdate,
)
from app.services.interview_service import interview_service

router = APIRouter(prefix="/interviews", tags=["Interviews"])


def _interview_response(interview) -> InterviewResponse:
    return InterviewResponse(
        id=str(interview.id),
        jobId=str(interview.job_id),
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


@router.get("", response_model=PaginatedResponse[InterviewResponse])
async def list_interviews(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = None,
    type: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    interviews, total = await interview_service.list_interviews(
        db, user, page=page, limit=limit, status=status, interview_type=type
    )
    return PaginatedResponse(
        data=[_interview_response(i) for i in interviews],
        total=total,
        page=page,
        limit=limit,
        total_pages=math.ceil(total / limit) if total > 0 else 0,
    )


@router.get("/{interview_id}", response_model=SuccessResponse[InterviewResponse])
async def get_interview(
    interview_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    interview = await interview_service.get_by_id(db, interview_id)
    return SuccessResponse(data=_interview_response(interview))


@router.post("", status_code=201, response_model=SuccessResponse[InterviewResponse])
async def create_interview(
    payload: InterviewCreate,
    employer: User = Depends(require_role(UserRole.EMPLOYER)),
    db: AsyncSession = Depends(get_db),
):
    interview = await interview_service.create(db, employer, payload)
    return SuccessResponse(data=_interview_response(interview))


@router.patch("/{interview_id}", response_model=SuccessResponse[InterviewResponse])
async def update_interview(
    interview_id: uuid.UUID,
    payload: InterviewUpdate,
    employer: User = Depends(require_role(UserRole.EMPLOYER)),
    db: AsyncSession = Depends(get_db),
):
    interview = await interview_service.update(db, interview_id, employer.id, payload)
    return SuccessResponse(data=_interview_response(interview))


@router.post("/{interview_id}/start", response_model=SuccessResponse[AIInterviewStartResponse])
async def start_ai_interview(
    interview_id: uuid.UUID,
    user: User = Depends(require_role(UserRole.JOB_SEEKER)),
    db: AsyncSession = Depends(get_db),
):
    interview = await interview_service.start_ai_interview(db, interview_id, user.id)
    return SuccessResponse(
        data=AIInterviewStartResponse(
            interviewId=str(interview.id),
            questions=interview.questions,
            totalQuestions=len(interview.questions),
        )
    )


@router.post("/{interview_id}/responses")
async def submit_responses(
    interview_id: uuid.UUID,
    payload: InterviewResponsesRequest,
    user: User = Depends(require_role(UserRole.JOB_SEEKER)),
    db: AsyncSession = Depends(get_db),
):
    await interview_service.submit_responses(db, interview_id, user.id, payload)
    return {"message": "Responses recorded"}


@router.get("/{interview_id}/results", response_model=SuccessResponse[AIInterviewResult])
async def get_results(
    interview_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    results = await interview_service.get_results(db, interview_id, user.id)
    return SuccessResponse(data=results)
