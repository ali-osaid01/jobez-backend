from datetime import date

from pydantic import BaseModel, Field

from app.core.enums import ExperienceLevel, JobStatus, JobType, LocationType


class JobCreate(BaseModel):
    title: str = Field(min_length=1)
    location: str = Field(min_length=1)
    locationType: LocationType
    salary: str = Field(min_length=1)
    type: JobType
    experienceLevel: ExperienceLevel
    description: str = Field(min_length=1)
    requirements: list[str] = []
    responsibilities: list[str] = []
    benefits: list[str] = []
    applicationDeadline: date | None = None


class JobUpdate(BaseModel):
    title: str | None = None
    location: str | None = None
    locationType: LocationType | None = None
    salary: str | None = None
    type: JobType | None = None
    experienceLevel: ExperienceLevel | None = None
    description: str | None = None
    requirements: list[str] | None = None
    responsibilities: list[str] | None = None
    benefits: list[str] | None = None
    applicationDeadline: date | None = None
    status: JobStatus | None = None


class JobResponse(BaseModel):
    id: str
    title: str
    company: str
    location: str
    locationType: str
    salary: str
    type: str
    experienceLevel: str
    description: str
    requirements: list[str]
    responsibilities: list[str]
    benefits: list[str]
    postedDate: date
    applicationDeadline: date | None = None
    employerId: str
    matchScore: float | None = None
    applicantsCount: int
    status: str
    createdAt: str
    updatedAt: str

    model_config = {"from_attributes": True}
