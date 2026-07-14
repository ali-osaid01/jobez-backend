import asyncio
import uuid
from datetime import date

import structlog
from sqlalchemy import func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import JobStatus
from app.core.exceptions import ForbiddenException, NotFoundException
from app.models.bookmark import Bookmark
from app.models.job import Job
from app.models.profile import Profile
from app.models.user import User
from app.schemas.job import JobCreate, JobUpdate
from app.services.matching import (
    MIN_APPLY_MATCH_SCORE,
    MatchResult,
    explain_candidate_job_match,
    score_candidate_job_match,
)
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


def _distance_to_match_score(distance: float | None) -> float | None:
    if distance is None:
        return None
    similarity = max(0.0, 1.0 - distance)
    return round(similarity * 100, 2)


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

    async def _get_job_seeker_profile(self, db: AsyncSession, user_id: uuid.UUID | None) -> Profile | None:
        if not user_id:
            return None
        stmt = select(Profile).where(Profile.user_id == user_id, Profile.role == "job-seeker")
        return (await db.execute(stmt)).scalar_one_or_none()

    async def get_by_id(
        self,
        db: AsyncSession,
        job_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> tuple[Job, str, bool, float | None, list[str]]:
        """Returns (Job, company_name, is_booked) by joining employer Profile."""
        if user_id:
            is_booked_col = (
                select(Bookmark.id)
                .where(Bookmark.job_id == Job.id, Bookmark.user_id == user_id)
                .correlate(Job)
                .exists()
                .label("is_booked")
            )
        else:
            is_booked_col = literal(False).label("is_booked")

        stmt = (
            select(Job, Profile.company, is_booked_col)
            .join(Profile, Profile.user_id == Job.employer_id)
            .where(Job.id == job_id)
            .limit(1)
        )
        result = await db.execute(stmt)
        row = result.first()
        if not row:
            raise NotFoundException("Job")
        job, company, is_booked = row
        match = None
        profile = await self._get_job_seeker_profile(db, user_id)
        if profile:
            match_result = await score_candidate_job_match(profile, job)
            match = (match_result.score, match_result.reasons)
        return job, company, is_booked, match[0] if match else None, match[1] if match else []

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
        user_id: uuid.UUID | None = None,
    ) -> tuple[list[tuple[Job, str, bool, float | None, list[str]]], int]:
        if user_id:
            is_booked_col = (
                select(Bookmark.id)
                .where(Bookmark.job_id == Job.id, Bookmark.user_id == user_id)
                .correlate(Job)
                .exists()
                .label("is_booked")
            )
        else:
            is_booked_col = literal(False).label("is_booked")

        stmt = select(Job, Profile.company, is_booked_col).join(Profile, Profile.user_id == Job.employer_id)

        if status and status != "all":
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
        rows = list(result.all())
        profile = await self._get_job_seeker_profile(db, user_id)
        if not profile:
            return [(job, company or "", bool(is_booked), None, []) for job, company, is_booked in rows], total

        scored_rows: list[tuple[Job, str, bool, float | None, list[str]]] = []
        for job, company, is_booked in rows:
            match_result = await score_candidate_job_match(profile, job)
            scored_rows.append((job, company or "", bool(is_booked), match_result.score, match_result.reasons))
        return scored_rows, total

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

        if job.status == JobStatus.ACTIVE:
            asyncio.create_task(_index_job(str(job.id), build_job_text(job)))

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

    async def get_recommended(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        *,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[tuple[Job, str, float | None, list[str]]], int]:
        profile_stmt = select(Profile).where(Profile.user_id == user_id)
        profile = (await db.execute(profile_stmt)).scalar_one_or_none()
        if not profile:
            logger.info("recommended_empty_no_profile", user_id=str(user_id))
            return [], 0

        async def fallback_recommendations() -> tuple[list[tuple[Job, str, float | None, list[str]]], int]:
            stmt = (
                select(Job, Profile.company)
                .join(Profile, Profile.user_id == Job.employer_id)
                .where(Job.status == JobStatus.ACTIVE)
                .order_by(Job.posted_date.desc())
            )
            result = await db.execute(stmt)
            scored: list[tuple[Job, str, float | None, list[str]]] = []
            for job, company in result.all():
                match_result = await score_candidate_job_match(profile, job)
                if match_result.score >= MIN_APPLY_MATCH_SCORE:
                    scored.append((job, company or "", match_result.score, match_result.reasons))
            scored.sort(key=lambda item: item[2] or 0, reverse=True)
            start = (page - 1) * limit
            return scored[start : start + limit], len(scored)

        # Try to fetch user's profile embedding from ChromaDB
        user_vec: list[float] | None = None
        try:
            result = get_resumes_collection().get(ids=[str(user_id)], include=["embeddings"])
            embeddings = result.get("embeddings") or []
            if embeddings and embeddings[0]:
                user_vec = embeddings[0]
        except Exception as exc:
            logger.warning("resume_embedding_fetch_failed", user_id=str(user_id), error=str(exc))

        if not user_vec:
            logger.info("recommended_empty_no_embedding", user_id=str(user_id))
            return await fallback_recommendations()

        # Cosine similarity query against jobs collection
        try:
            jobs_collection = get_jobs_collection()
            collection_count = jobs_collection.count()
            if collection_count <= 0:
                logger.info("recommended_empty_no_jobs_indexed", user_id=str(user_id))
                return await fallback_recommendations()
            chroma_result = jobs_collection.query(
                query_embeddings=[user_vec],
                n_results=collection_count,
                include=["distances"],
            )
            job_id_strs: list[str] = chroma_result["ids"][0] if chroma_result["ids"] else []
            distances: list[float | None] = chroma_result.get("distances", [[]])[0] if chroma_result.get("distances") else []
        except Exception as exc:
            logger.error("chroma_query_failed", user_id=str(user_id), error=str(exc))
            return await fallback_recommendations()

        if not job_id_strs:
            logger.info("recommended_empty_chroma_result", user_id=str(user_id))
            return [], 0

        # Fetch matching jobs from Postgres (with company join)
        job_uuids = [uuid.UUID(jid) for jid in job_id_strs]
        stmt = (
            select(Job, Profile.company)
            .join(Profile, Profile.user_id == Job.employer_id)
            .where(Job.id.in_(job_uuids), Job.status == JobStatus.ACTIVE)
        )
        rows = await db.execute(stmt)
        jobs_by_id: dict[str, tuple[Job, str]] = {str(job.id): (job, company or "") for job, company in rows.all()}

        # Return in ChromaDB similarity order, with a minimum score threshold.
        ordered_jobs: list[tuple[Job, str, float | None, list[str]]] = []
        for index, jid in enumerate(job_id_strs):
            if jid not in jobs_by_id:
                continue
            score = _distance_to_match_score(distances[index] if index < len(distances) else None)
            job, company = jobs_by_id[jid]
            match_result = explain_candidate_job_match(profile, job, embedding_score=score)
            if match_result.score < MIN_APPLY_MATCH_SCORE:
                continue
            ordered_jobs.append((job, company, match_result.score, match_result.reasons))

        if not ordered_jobs:
            logger.info("recommended_empty_below_threshold", user_id=str(user_id))
            return [], 0
        start = (page - 1) * limit
        return ordered_jobs[start : start + limit], len(ordered_jobs)

    async def get_saved(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        *,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[tuple[Job, str, bool, float | None, list[str]]], int]:
        stmt = (
            select(Job, Profile.company, literal(True).label("is_booked"))
            .join(Bookmark, Bookmark.job_id == Job.id)
            .join(Profile, Profile.user_id == Job.employer_id)
            .where(Bookmark.user_id == user_id)
            .order_by(Bookmark.created_at.desc())
        )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        result = await db.execute(stmt.offset((page - 1) * limit).limit(limit))
        rows = list(result.all())
        profile = await self._get_job_seeker_profile(db, user_id)
        if not profile:
            return [(job, company or "", bool(is_booked), None, []) for job, company, is_booked in rows], total

        scored_rows: list[tuple[Job, str, bool, float | None, list[str]]] = []
        for job, company, is_booked in rows:
            match_result = await score_candidate_job_match(profile, job)
            scored_rows.append((job, company or "", bool(is_booked), match_result.score, match_result.reasons))
        return scored_rows, total


job_service = JobService()
