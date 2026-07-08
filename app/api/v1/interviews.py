import math
import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.core.enums import UserRole
from app.core.exceptions import ForbiddenException, NotFoundException
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.interview import (
    AIInterviewResult,
    AIInterviewStartResponse,
    InterviewAnswerTranscriptResponse,
    InterviewCreate,
    InterviewCounts,
    InterviewListResponse,
    InterviewResponse,
    InterviewResponsesRequest,
    InterviewUpdate,
)
from app.services.openai_voice_service import openai_voice_service
from app.services.interview_service import interview_service

router = APIRouter(prefix="/interviews", tags=["Interviews"])


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


@router.get("", response_model=InterviewListResponse)
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
    raw_counts = await interview_service.get_status_counts(db, user, interview_type=type)
    return InterviewListResponse(
        data=[_interview_response(i) for i in interviews],
        total=total,
        page=page,
        limit=limit,
        total_pages=math.ceil(total / limit) if total > 0 else 0,
        counts=InterviewCounts(**raw_counts),
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


@router.get("/{interview_id}/questions/{question_id}/audio")
async def get_question_audio(
    interview_id: uuid.UUID,
    question_id: str,
    user: User = Depends(require_role(UserRole.JOB_SEEKER)),
    db: AsyncSession = Depends(get_db),
):
    interview = await interview_service.get_by_id(db, interview_id)
    if interview.applicant_id != user.id:
        raise ForbiddenException("You can only access your own interview audio")

    questions = interview.questions or []
    question = next((q for q in questions if q.get("id") == question_id), None)
    if not question:
        raise NotFoundException("Question")

    audio_bytes = await openai_voice_service.text_to_speech(question["question"])

    return Response(content=audio_bytes, media_type="audio/mpeg")


@router.post("/{interview_id}/questions/{question_id}/transcribe", response_model=SuccessResponse[InterviewAnswerTranscriptResponse])
async def transcribe_answer(
    interview_id: uuid.UUID,
    question_id: str,
    audio: UploadFile = File(...),
    duration: int = Form(0),
    timestamp: str = Form(...),
    user: User = Depends(require_role(UserRole.JOB_SEEKER)),
    db: AsyncSession = Depends(get_db),
):
    interview = await interview_service.get_by_id(db, interview_id)
    if interview.applicant_id != user.id:
        raise ForbiddenException("You can only transcribe your own interview answers")

    content = await audio.read()
    transcript = await openai_voice_service.transcribe_audio(
        filename=audio.filename or f"{question_id}.webm",
        content=content,
        content_type=audio.content_type,
    )
    return SuccessResponse(
        data=InterviewAnswerTranscriptResponse(
            interviewId=str(interview.id),
            questionId=question_id,
            transcript=transcript,
            duration=duration,
            timestamp=timestamp,
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
