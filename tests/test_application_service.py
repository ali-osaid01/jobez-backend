import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import ValidationError
from app.core.enums import (
    ApplicationStatus,
    ExperienceLevel,
    InterviewStatus,
    InterviewType,
    JobStatus,
    JobType,
    LocationType,
    UserRole,
)
from app.models.job import Job
from app.models.profile import Profile
from app.schemas.application import ApplicationCreate
from app.services.application_service import INTERVIEW_MATCH_THRESHOLD, ApplicationService


class FakeResult:
    def __init__(self, row=None, scalar=None):
        self._row = row
        self._scalar = scalar

    def one_or_none(self):
        return self._row

    def scalar_one_or_none(self):
        return self._scalar


class FakeSession:
    def __init__(self, results):
        self.results = list(results)
        self.added = []
        self.flushed = False

    async def execute(self, _stmt):
        return self.results.pop(0)

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flushed = True


def _build_job() -> Job:
    job = Job(
        id=uuid.uuid4(),
        employer_id=uuid.uuid4(),
        title="Backend Engineer",
        location="Remote",
        location_type=LocationType.REMOTE,
        salary="150000",
        type=JobType.FULL_TIME,
        experience_level=ExperienceLevel.MID,
        description="Build APIs with Python and FastAPI.",
        requirements=["Python", "FastAPI", "PostgreSQL"],
        responsibilities=["Build APIs"],
        benefits=["Remote work"],
        posted_date=date.today(),
        application_deadline=None,
        applicants_count=0,
        status=JobStatus.ACTIVE,
    )
    return job


def _build_profile() -> Profile:
    return Profile(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name="Jane Doe",
        email="jane@example.com",
        phone="1234567890",
        role=UserRole.JOB_SEEKER.value,
        title="Backend Engineer",
        location="Remote",
        experience="5 years",
        preferred_role="Backend Engineer",
        expected_salary="150000",
        skills=["Python", "FastAPI", "PostgreSQL"],
        education=[],
        work_experience=[],
        certifications=[],
        resume=None,
        bio="Backend engineer focused on APIs.",
        company=None,
        company_size=None,
        industry=None,
        website=None,
        description=None,
        founded=None,
    )


def _build_social_media_job() -> Job:
    job = _build_job()
    job.title = "Social Media Manager"
    job.description = "Create social campaigns, manage Instagram content, and report engagement metrics."
    job.requirements = ["Social media strategy", "Content calendar", "Instagram analytics"]
    job.responsibilities = ["Plan posts", "Coordinate campaigns"]
    job.benefits = ["Flexible hours"]
    return job


@pytest.mark.asyncio
async def test_create_auto_schedules_interview_for_high_match(monkeypatch):
    service = ApplicationService()
    job = _build_job()
    profile = _build_profile()
    applicant = SimpleNamespace(
        id=profile.user_id,
        name=profile.name,
        email=profile.email,
        role=UserRole.JOB_SEEKER,
    )
    interview = SimpleNamespace(
        id=uuid.uuid4(),
        job_id=job.id,
        application_id=uuid.uuid4(),
        applicant_id=profile.user_id,
        job_title=job.title,
        company="Acme",
        applicant_name=applicant.name,
        scheduled_date=date.today().isoformat(),
        scheduled_time="00:00",
        duration=30,
        status=InterviewStatus.SCHEDULED,
        type=InterviewType.AI,
        meeting_link=None,
        notes=None,
        ai_score=None,
        ai_summary=None,
        created_at=date.today(),
        updated_at=date.today(),
    )
    fake_db = FakeSession(
        [
            FakeResult(row=(job, "Acme")),
            FakeResult(scalar=profile),
            FakeResult(scalar=None),
        ]
    )

    monkeypatch.setattr(service, "_score_application", AsyncMock(return_value=INTERVIEW_MATCH_THRESHOLD + 5))
    monkeypatch.setattr(service, "_create_auto_interview", AsyncMock(return_value=interview))

    application, created_interview = await service.create(
        fake_db,
        applicant,
        ApplicationCreate(jobId=str(job.id)),
    )

    assert fake_db.flushed is True
    assert job.applicants_count == 1
    assert application.status == ApplicationStatus.INTERVIEW_SCHEDULED
    assert application.match_score == INTERVIEW_MATCH_THRESHOLD + 5
    assert created_interview is interview


@pytest.mark.asyncio
async def test_create_keeps_application_pending_for_low_match(monkeypatch):
    service = ApplicationService()
    job = _build_job()
    profile = _build_profile()
    applicant = SimpleNamespace(
        id=profile.user_id,
        name=profile.name,
        email=profile.email,
        role=UserRole.JOB_SEEKER,
    )
    fake_db = FakeSession(
        [
            FakeResult(row=(job, "Acme")),
            FakeResult(scalar=profile),
            FakeResult(scalar=None),
        ]
    )

    monkeypatch.setattr(service, "_score_application", AsyncMock(return_value=INTERVIEW_MATCH_THRESHOLD - 10))
    create_auto_interview = AsyncMock()
    monkeypatch.setattr(service, "_create_auto_interview", create_auto_interview)

    application, created_interview = await service.create(
        fake_db,
        applicant,
        ApplicationCreate(jobId=str(job.id)),
    )

    assert fake_db.flushed is True
    assert job.applicants_count == 1
    assert application.status == ApplicationStatus.PENDING
    assert application.match_score == INTERVIEW_MATCH_THRESHOLD - 10
    assert created_interview is None
    create_auto_interview.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_blocks_low_relevance_application_before_saving(monkeypatch):
    service = ApplicationService()
    job = _build_social_media_job()
    profile = _build_profile()
    applicant = SimpleNamespace(
        id=profile.user_id,
        name=profile.name,
        email=profile.email,
        role=UserRole.JOB_SEEKER,
    )
    fake_db = FakeSession(
        [
            FakeResult(row=(job, "Acme")),
            FakeResult(scalar=profile),
        ]
    )
    score_application = AsyncMock(return_value=90)
    monkeypatch.setattr(service, "_score_application", score_application)

    with pytest.raises(ValidationError):
        await service.create(fake_db, applicant, ApplicationCreate(jobId=str(job.id)))

    assert fake_db.added == []
    assert fake_db.flushed is False
    assert job.applicants_count == 0
    score_application.assert_not_awaited()
