import asyncio
import uuid
from datetime import date

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import JobStatus
from app.core.exceptions import ForbiddenException, NotFoundException
from app.models.bookmark import Bookmark
from app.models.job import Job
from app.models.profile import Profile
from app.models.user import User
from app.schemas.job import JobCreate, JobUpdate
from app.vectordb.collections import get_jobs_collection, get_resumes_collection
from app.vectordb.embeddings import build_job_text, embed_text

logger = structlog.get_logger()


async def _index_job(job_id: str, text: str) -> None:
    """Embed a job and upsert into ChromaDB. Runs as a background task."""
    try:
        vec = await embed_text(text)
        if not vec:
            return
        get_jobs_collection().upsert(ids=[job_id], embeddings=[vec], documents=[text])
        logger.info("job_indexed", job_id=job_id)
    except Exception as exc:
        logger.error("job_index_failed", job_id=job_id, error=str(exc))


class JobService:
    async def create(self, db: AsyncSession, employer: User, data: JobCreate) -> Job:
        job = Job(
            id=uuid.uuid4(),
            employer_id=employer.id,
            title=data.title,
            location=data.location,
            location_type=data.locationType,
            salary=data.salary,
            type=data.type,
            experience_level=data.experienceLevel,
            description=data.description,
            requirements=data.requirements,
            responsibilities=data.responsibilities,
            benefits=data.benefits,
            posted_date=date.today(),
            application_deadline=data.applicationDeadline,
            applicants_count=0,
            status=JobStatus.ACTIVE,
        )
        db.add(job)
        await db.flush()
        await db.refresh(job)
        asyncio.create_task(_index_job(str(job.id), build_job_text(job)))
        return job

    async def _get_job(self, db: AsyncSession, job_id: uuid.UUID) -> Job:
        """Internal use — returns Job only (no company join). Used by update/delete/bookmark."""
        stmt = select(Job).where(Job.id == job_id)
        result = await db.execute(stmt)
        job = result.scalar_one_or_none()
        if not job:
            raise NotFoundException("Job")
        return job

    async def get_employer_company_name(self, db: AsyncSession, employer_id: uuid.UUID) -> str:
        stmt = select(Profile.company).where(Profile.user_id == employer_id).limit(1)
        return (await db.execute(stmt)).scalar_one_or_none() or ""

    async def get_by_id(self, db: AsyncSession, job_id: uuid.UUID) -> tuple[Job, str]:
        """Returns (Job, company_name) by joining employer Profile."""
        stmt = (
            select(Job, Profile.company)
            .join(Profile, Profile.user_id == Job.employer_id)
            .where(Job.id == job_id)
            .limit(1)
        )
        result = await db.execute(stmt)
        row = result.first()
        if not row:
            raise NotFoundException("Job")
        return row  # (Job, company_str)

    async def list_jobs(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        limit: int = 20,
        search: str | None = None,
        location_type: str | None = None,
        job_type: str | None = None,
        experience_level: str | None = None,
        employer_id: uuid.UUID | None = None,
        status: str | None = "active",
        sort_by: str | None = "postedDate",
        sort_order: str | None = "desc",
    ) -> tuple[list[tuple[Job, str]], int]:
        stmt = select(Job, Profile.company).join(Profile, Profile.user_id == Job.employer_id)

        if status:
            stmt = stmt.where(Job.status == status)
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                Job.title.ilike(pattern) | Profile.company.ilike(pattern) | Job.location.ilike(pattern)
            )

        if location_type:
            stmt = stmt.where(Job.location_type == location_type)
        if job_type:
            stmt = stmt.where(Job.type == job_type)
        if experience_level:
            stmt = stmt.where(Job.experience_level == experience_level)
        if employer_id:
            stmt = stmt.where(Job.employer_id == employer_id)

        # Count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        # Sort
        sort_col = Job.created_at
        if sort_by == "postedDate":
            sort_col = Job.posted_date
        elif sort_by == "salary":
            sort_col = Job.salary

        if sort_order == "asc":
            stmt = stmt.order_by(sort_col.asc())
        else:
            stmt = stmt.order_by(sort_col.desc())

        # Paginate
        stmt = stmt.offset((page - 1) * limit).limit(limit)
        result = await db.execute(stmt)
        return list(result.all()), total  # list of (Job, company_str)

    async def update(self, db: AsyncSession, job_id: uuid.UUID, employer_id: uuid.UUID, data: JobUpdate) -> tuple[Job, str]:
        job = await self._get_job(db, job_id)
        if job.employer_id != employer_id:
            raise ForbiddenException("You can only edit your own jobs")

        update_data = data.model_dump(exclude_unset=True)
        field_mapping = {
            "locationType": "location_type",
            "experienceLevel": "experience_level",
            "applicationDeadline": "application_deadline",
        }
        for key, value in update_data.items():
            db_field = field_mapping.get(key, key)
            if hasattr(job, db_field):
                setattr(job, db_field, value)

        await db.flush()
        await db.refresh(job)

        # Fetch company from profile for the response
        stmt = select(Profile.company).where(Profile.user_id == employer_id)
        company = (await db.execute(stmt)).scalar_one_or_none() or ""
        return job, company

    async def delete(self, db: AsyncSession, job_id: uuid.UUID, employer_id: uuid.UUID) -> None:
        job = await self._get_job(db, job_id)
        if job.employer_id != employer_id:
            raise ForbiddenException("You can only delete your own jobs")
        job.status = JobStatus.CLOSED
        await db.flush()

    async def toggle_bookmark(self, db: AsyncSession, user_id: uuid.UUID, job_id: uuid.UUID) -> bool:
        await self._get_job(db, job_id)

        stmt = select(Bookmark).where(Bookmark.user_id == user_id, Bookmark.job_id == job_id)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            await db.delete(existing)
            await db.flush()
            return False
        else:
            bookmark = Bookmark(id=uuid.uuid4(), user_id=user_id, job_id=job_id)
            db.add(bookmark)
            await db.flush()
            return True

    async def get_recommended(self, db: AsyncSession, user_id: uuid.UUID) -> list[tuple[Job, str]]:
        # Try to fetch user's profile embedding from ChromaDB
        user_vec: list[float] | None = None
        try:
            result = get_resumes_collection().get(ids=[str(user_id)], include=["embeddings"])
            embeddings = result.get("embeddings") or []
            if embeddings and embeddings[0]:
                user_vec = embeddings[0]
        except Exception as exc:
            logger.warning("resume_embedding_fetch_failed", user_id=str(user_id), error=str(exc))

        # Fallback: no embedding yet → return latest active jobs
        if not user_vec:
            logger.info("recommended_fallback_latest", user_id=str(user_id))
            stmt = (
                select(Job, Profile.company)
                .join(Profile, Profile.user_id == Job.employer_id)
                .where(Job.status == JobStatus.ACTIVE)
                .order_by(Job.created_at.desc())
                .limit(10)
            )
            rows = await db.execute(stmt)
            return list(rows.all())

        # Cosine similarity query against jobs collection
        try:
            chroma_result = get_jobs_collection().query(
                query_embeddings=[user_vec],
                n_results=10,
                include=["distances"],
            )
            job_id_strs: list[str] = chroma_result["ids"][0] if chroma_result["ids"] else []
        except Exception as exc:
            logger.error("chroma_query_failed", user_id=str(user_id), error=str(exc))
            return []

        if not job_id_strs:
            return []

        # Fetch matching jobs from Postgres (with company join)
        job_uuids = [uuid.UUID(jid) for jid in job_id_strs]
        stmt = (
            select(Job, Profile.company)
            .join(Profile, Profile.user_id == Job.employer_id)
            .where(Job.id.in_(job_uuids), Job.status == JobStatus.ACTIVE)
        )
        rows = await db.execute(stmt)
        jobs_by_id: dict[str, tuple[Job, str]] = {str(job.id): (job, company or "") for job, company in rows.all()}

        # Return in ChromaDB similarity order
        return [jobs_by_id[jid] for jid in job_id_strs if jid in jobs_by_id]


job_service = JobService()
