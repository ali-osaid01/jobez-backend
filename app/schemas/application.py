from datetime import date

from pydantic import BaseModel

from app.core.enums import ApplicationStatus
from app.schemas.interview import InterviewResponse
from app.schemas.common import PaginatedResponse


class ApplicationCreate(BaseModel):
    jobId: str
    resume: str | None = None
    coverLetter: str | None = None


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus
    rejectionReason: str | None = None


class ApplicationResponse(BaseModel):
    id: str
    jobId: str
    jobTitle: str
    company: str
    applicantId: str
    applicantName: str
    applicantEmail: str
    status: str
    appliedDate: date
    resume: str | None = None
    coverLetter: str | None = None
    matchScore: float | None = None
    rejectionReason: str | None = None
    latestInterviewId: str | None = None
    latestInterviewStatus: str | None = None
    latestInterviewType: str | None = None
    latestInterviewScore: float | None = None
    latestInterviewSummary: str | None = None
    createdAt: str
    updatedAt: str

    model_config = {"from_attributes": True}


class ApplicationCounts(BaseModel):
    total: int
    pending: int
    shortlisted: int
    interviewScheduled: int
    rejected: int = 0
    hired: int = 0


class ApplicationListResponse(PaginatedResponse[ApplicationResponse]):
    counts: ApplicationCounts | None = None


class ApplicationApplyResponse(BaseModel):
    application: ApplicationResponse
    interview: InterviewResponse | None = None
    eligibleForInterview: bool = False
    interviewThreshold: float | None = None
