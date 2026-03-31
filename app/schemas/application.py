from datetime import date

from pydantic import BaseModel

from app.core.enums import ApplicationStatus


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
    createdAt: str
    updatedAt: str

    model_config = {"from_attributes": True}
