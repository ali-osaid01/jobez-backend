from pydantic import AliasChoices, BaseModel, Field

from app.core.enums import InterviewType
from app.schemas.common import PaginatedResponse


class InterviewCreate(BaseModel):
    jobId: str
    applicantId: str
    scheduledDate: str
    scheduledTime: str
    duration: int = 30
    type: InterviewType


class InterviewUpdate(BaseModel):
    scheduledDate: str | None = None
    scheduledTime: str | None = None
    duration: int | None = None
    status: str | None = None
    meetingLink: str | None = None
    notes: str | None = None


class InterviewResponse(BaseModel):
    id: str
    jobId: str
    applicationId: str
    jobTitle: str
    company: str
    applicantId: str
    applicantName: str | None = None
    scheduledDate: str
    scheduledTime: str
    duration: int
    status: str
    type: str
    meetingLink: str | None = None
    notes: str | None = None
    aiScore: float | None = None
    aiSummary: str | None = None
    createdAt: str
    updatedAt: str

    model_config = {"from_attributes": True}


class InterviewCounts(BaseModel):
    total: int
    scheduled: int
    inProgress: int = 0
    completed: int
    cancelled: int


class InterviewListResponse(PaginatedResponse[InterviewResponse]):
    counts: InterviewCounts


class AIInterviewQuestion(BaseModel):
    id: str
    question: str
    type: str
    category: str
    expectedDuration: int


class AIInterviewStartResponse(BaseModel):
    interviewId: str
    questions: list[AIInterviewQuestion]
    totalQuestions: int


class InterviewResponseSubmission(BaseModel):
    questionId: str
    response: str = Field(validation_alias=AliasChoices("response", "answer"), serialization_alias="response")
    duration: int
    timestamp: str


class InterviewAnswerTranscriptResponse(BaseModel):
    interviewId: str
    questionId: str
    transcript: str
    duration: int
    timestamp: str


class InterviewResponsesRequest(BaseModel):
    responses: list[InterviewResponseSubmission]


class AIInterviewResult(BaseModel):
    interviewId: str
    overallScore: float
    technicalScore: float
    communicationScore: float
    problemSolvingScore: float
    cultureFitScore: float
    strengths: list[str]
    improvements: list[str]
    summary: str
    responses: list[InterviewResponseSubmission]
