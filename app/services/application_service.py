import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ApplicationStatus, JobStatus
from app.core.exceptions import ConflictException, InvalidTransitionException, NotFoundException
from app.models.application import Application
from app.models.job import Job
from app.models.profile import Profile
from app.models.user import User
from app.schemas.application import ApplicationCreate, ApplicationStatusUpdate

VALID_TRANSITIONS: dict[ApplicationStatus, set[ApplicationStatus]] = {
    ApplicationStatus.PENDING: {ApplicationStatus.SHORTLISTED, ApplicationStatus.REJECTED},
    ApplicationStatus.SHORTLISTED: {ApplicationStatus.INTERVIEW_SCHEDULED, ApplicationStatus.REJECTED},
    ApplicationStatus.INTERVIEW_SCHEDULED: {ApplicationStatus.HIRED, ApplicationStatus.REJECTED},
}


class ApplicationService:
    async def create(self, db: AsyncSession, applicant: User, data: ApplicationCreate) -> Application:
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
        db.add(application)

        # Increment applicants count
        job.applicants_count += 1

        await db.flush()
        return application

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

    async def update_status(
        self, db: AsyncSession, app_id: uuid.UUID, employer_id: uuid.UUID, data: ApplicationStatusUpdate
    ) -> Application:
        stmt = select(Application).join(Job).where(Application.id == app_id, Job.employer_id == employer_id)
        result = await db.execute(stmt)
        application = result.scalar_one_or_none()
        if not application:
            raise NotFoundException("Application")

        current = ApplicationStatus(application.status)
        allowed = VALID_TRANSITIONS.get(current, set())
        if data.status not in allowed:
            raise InvalidTransitionException(
                f"Cannot transition from '{current.value}' to '{data.status.value}'"
            )

        application.status = data.status
        if data.rejectionReason and data.status == ApplicationStatus.REJECTED:
            application.rejection_reason = data.rejectionReason

        await db.flush()
        await db.refresh(application)  # Refresh to get updated timestamps
        return application

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
