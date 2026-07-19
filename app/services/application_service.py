import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ApplicationStatus, InterviewStatus, InterviewType, JobStatus
from app.core.exceptions import ConflictException, InvalidTransitionException, NotFoundException, ValidationError
from app.models.interview import Interview
from app.models.application import Application
from app.models.job import Job
from app.models.profile import Profile
from app.models.user import User
from app.schemas.application import ApplicationCreate, ApplicationStatusUpdate
from app.services.matching import (
    AUTO_INTERVIEW_MATCH_SCORE,
    MIN_APPLY_MATCH_SCORE,
    MatchResult,
    score_candidate_job_match,
)
from app.services.notification_service import notification_service

VALID_TRANSITIONS: dict[ApplicationStatus, set[ApplicationStatus]] = {
    ApplicationStatus.PENDING: {ApplicationStatus.SHORTLISTED, ApplicationStatus.REJECTED},
    ApplicationStatus.SHORTLISTED: {ApplicationStatus.INTERVIEW_SCHEDULED, ApplicationStatus.REJECTED},
    ApplicationStatus.INTERVIEW_SCHEDULED: {ApplicationStatus.HIRED, ApplicationStatus.REJECTED},
}

INTERVIEW_MATCH_THRESHOLD = AUTO_INTERVIEW_MATCH_SCORE


class ApplicationService:
    async def _score_application(self, profile: Profile | None, job: Job) -> MatchResult:
        return await score_candidate_job_match(profile, job)

    async def _create_auto_interview(
        self,
        db: AsyncSession,
        *,
        job: Job,
        company: str,
        application: Application,
    ) -> Interview:
        interview = Interview(
            id=uuid.uuid4(),
            job_id=job.id,
            application_id=application.id,
            applicant_id=application.applicant_id,
            job_title=job.title,
            company=company or "",
            applicant_name=application.applicant_name,
            scheduled_date=date.today().isoformat(),
            scheduled_time="00:00",
            duration=30,
            status=InterviewStatus.SCHEDULED,
            type=InterviewType.AI,
        )
        db.add(interview)
        return interview

    async def create(self, db: AsyncSession, applicant: User, data: ApplicationCreate) -> tuple[Application, Interview | None]:
        job_id = uuid.UUID(data.jobId)

        # Get job + company from employer profile
        stmt = (
            select(Job, Profile.company)
            .join(Profile, Profile.user_id == Job.employer_id)
            .where(Job.id == job_id)
        )
        result = await db.execute(stmt)
        row = result.one_or_none()
        if not row:
            raise NotFoundException("Job")
        job, company = row
        if job.status != JobStatus.ACTIVE:
            raise NotFoundException("Job not found or closed")

        profile_stmt = select(Profile).where(Profile.user_id == applicant.id)
        profile = (await db.execute(profile_stmt)).scalar_one_or_none()

        # Check duplicate
        stmt = select(Application).where(
            Application.job_id == job_id, Application.applicant_id == applicant.id
        )
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise ConflictException("Already applied to this job")

        application = Application(
            id=uuid.uuid4(),
            job_id=job_id,
            applicant_id=applicant.id,
            job_title=job.title,
            company=company or "",
            applicant_name=applicant.name,
            applicant_email=applicant.email,
            status=ApplicationStatus.PENDING,
            applied_date=date.today(),
            resume=data.resume,
            cover_letter=data.coverLetter,
        )

        match_result = await self._score_application(profile, job)
        application.match_score = match_result.score

        if match_result.score < MIN_APPLY_MATCH_SCORE:
            raise ValidationError(
                f"Your match score is {match_result.score}%; minimum required is {MIN_APPLY_MATCH_SCORE:.0f}%. "
                "Update your profile or apply to a more relevant job."
            )

        db.add(application)

        interview: Interview | None = None
        if application.match_score >= AUTO_INTERVIEW_MATCH_SCORE:
            application.status = ApplicationStatus.INTERVIEW_SCHEDULED
            interview = await self._create_auto_interview(
                db,
                job=job,
                company=company or "",
                application=application,
            )

        # Increment applicants count
        job.applicants_count += 1

        await db.flush()
        return application, interview

    async def list_applications(
        self,
        db: AsyncSession,
        user: User,
        *,
        page: int = 1,
        limit: int = 20,
        status: str | None = None,
        job_id: str | None = None,
        search: str | None = None,
    ) -> tuple[list[Application], int]:
        stmt = select(Application)

        if user.role.value == "job-seeker":
            stmt = stmt.where(Application.applicant_id == user.id)
        else:
            # Employer: applications for their jobs
            stmt = stmt.join(Job).where(Job.employer_id == user.id)

        if status:
            stmt = stmt.where(Application.status == status)
        if job_id:
            stmt = stmt.where(Application.job_id == uuid.UUID(job_id))
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                Application.applicant_name.ilike(pattern) | Application.job_title.ilike(pattern)
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await db.scalar(count_stmt)

        stmt = stmt.order_by(Application.created_at.desc()).offset((page - 1) * limit).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_status_counts(
        self,
        db: AsyncSession,
        user: User,
        *,
        job_id: str | None = None,
        search: str | None = None,
    ) -> dict:
        stmt = select(Application.status, func.count().label("cnt"))

        if user.role.value == "job-seeker":
            stmt = stmt.where(Application.applicant_id == user.id)
        else:
            stmt = stmt.join(Job).where(Job.employer_id == user.id)

        if job_id:
            stmt = stmt.where(Application.job_id == uuid.UUID(job_id))
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                Application.applicant_name.ilike(pattern) | Application.job_title.ilike(pattern)
            )

        stmt = stmt.group_by(Application.status)
        result = await db.execute(stmt)
        rows = result.all()
        counts = {row.status: row.cnt for row in rows}
        total = sum(counts.values())
        return {
            "total": total,
            "pending": counts.get(ApplicationStatus.PENDING, 0),
            "shortlisted": counts.get(ApplicationStatus.SHORTLISTED, 0),
            "interviewScheduled": counts.get(ApplicationStatus.INTERVIEW_SCHEDULED, 0),
            "rejected": counts.get(ApplicationStatus.REJECTED, 0),
            "hired": counts.get(ApplicationStatus.HIRED, 0),
        }

    async def update_status(
        self, db: AsyncSession, app_id: uuid.UUID, employer_id: uuid.UUID, data: ApplicationStatusUpdate
    ) -> Application:
        stmt = select(Application, Job).join(Job).where(Application.id == app_id, Job.employer_id == employer_id)
        result = await db.execute(stmt)
        row = result.one_or_none()
        if not row:
            raise NotFoundException("Application")
        application, job = row

        current = ApplicationStatus(application.status)
        allowed = VALID_TRANSITIONS.get(current, set())
        if data.status not in allowed:
            raise InvalidTransitionException(
                f"Cannot transition from '{current.value}' to '{data.status.value}'"
            )
        if data.status == ApplicationStatus.REJECTED and not (data.rejectionReason or "").strip():
            raise ValidationError("Rejection reason is required")

        application.status = data.status
        if data.status == ApplicationStatus.REJECTED:
            application.rejection_reason = data.rejectionReason.strip()
        elif data.status == ApplicationStatus.HIRED:
            application.rejection_reason = None

        await self._create_status_notifications(
            db,
            application=application,
            job=job,
            employer_id=employer_id,
            status=data.status,
        )

        await db.flush()
        await db.refresh(application)
        return application

    async def _create_status_notifications(
        self,
        db: AsyncSession,
        *,
        application: Application,
        job: Job,
        employer_id: uuid.UUID,
        status: ApplicationStatus,
    ) -> None:
        notification_data = {
            "applicationId": str(application.id),
            "jobId": str(application.job_id),
            "jobTitle": application.job_title,
            "applicantId": str(application.applicant_id),
            "status": status.value,
        }

        if status == ApplicationStatus.REJECTED:
            reason = application.rejection_reason or "No reason provided."
            await notification_service.create(
                db,
                recipient_id=application.applicant_id,
                title="Application rejected",
                message=f"{application.company} rejected your application for {application.job_title}. Reason: {reason}",
                type="rejection",
                data=notification_data,
            )
            await notification_service.create(
                db,
                recipient_id=employer_id,
                title="Candidate rejected",
                message=f"You rejected {application.applicant_name} for {application.job_title}. Reason: {reason}",
                type="rejection",
                data=notification_data,
            )
        elif status == ApplicationStatus.HIRED:
            await notification_service.create(
                db,
                recipient_id=application.applicant_id,
                title="Application marked hired",
                message=f"{application.company} marked you as hired for {application.job_title}.",
                type="hired",
                data=notification_data,
            )
            await notification_service.create(
                db,
                recipient_id=employer_id,
                title="Candidate marked hired",
                message=f"You marked {application.applicant_name} as hired for {application.job_title}.",
                type="hired",
                data=notification_data,
            )
        elif status == ApplicationStatus.SHORTLISTED:
            await notification_service.create(
                db,
                recipient_id=application.applicant_id,
                title="Application shortlisted",
                message=f"{application.company} shortlisted your application for {application.job_title}.",
                type="application",
                data=notification_data,
            )
        elif status == ApplicationStatus.INTERVIEW_SCHEDULED:
            await notification_service.create(
                db,
                recipient_id=application.applicant_id,
                title="Interview scheduled",
                message=f"{application.company} scheduled an interview for {application.job_title}.",
                type="interview",
                data=notification_data,
            )

    async def get_resume_url(self, db: AsyncSession, app_id: uuid.UUID, employer_id: uuid.UUID) -> str:
        stmt = select(Application).join(Job).where(Application.id == app_id, Job.employer_id == employer_id)
        result = await db.execute(stmt)
        application = result.scalar_one_or_none()
        if not application:
            raise NotFoundException("Application")
        if not application.resume:
            raise NotFoundException("Resume")
        return application.resume

    async def contact_applicant(self, db: AsyncSession, app_id: uuid.UUID, employer_id: uuid.UUID) -> None:
        stmt = select(Application).join(Job).where(Application.id == app_id, Job.employer_id == employer_id)
        result = await db.execute(stmt)
        application = result.scalar_one_or_none()
        if not application:
            raise NotFoundException("Application")
        if ApplicationStatus(application.status) != ApplicationStatus.SHORTLISTED:
            raise InvalidTransitionException("Can only contact shortlisted applicants")
        # In production, this would trigger an email/notification
        pass


application_service = ApplicationService()
