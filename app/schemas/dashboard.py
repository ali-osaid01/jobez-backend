from pydantic import BaseModel

from app.schemas.application import ApplicationResponse
from app.schemas.interview import InterviewResponse
from app.schemas.job import JobResponse


class JobSeekerDashboard(BaseModel):
    totalApplications: int
    scheduledInterviews: int
    profileViews: int
    recentApplications: list[ApplicationResponse]
    upcomingInterviews: list[InterviewResponse]
    recommendedJobs: list[JobResponse]


class EmployerPipeline(BaseModel):
    applied: int
    aiInterviewDone: int
    shortlisted: int
    contacted: int
    offerSent: int
    hired: int


class EmployerDashboard(BaseModel):
    activeJobs: int
    totalApplicants: int
    shortlisted: int
    contacted: int
    pipeline: EmployerPipeline
    activeJobPostings: list[JobResponse]
    recentApplicants: list[ApplicationResponse]
