import math
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.core.enums import UserRole
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.schemas.job import JobCreate, JobResponse, JobUpdate
from app.services.job_service import job_service

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def _job_response(job, company: str) -> JobResponse:
    return JobResponse(
        id=str(job.id),
        title=job.title,
        company=company,
        location=job.location,
        locationType=job.location_type.value if hasattr(job.location_type, "value") else job.location_type,
        salary=job.salary,
        type=job.type.value if hasattr(job.type, "value") else job.type,
        experienceLevel=job.experience_level.value if hasattr(job.experience_level, "value") else job.experience_level,
        description=job.description,
        requirements=job.requirements or [],
        responsibilities=job.responsibilities or [],
        benefits=job.benefits or [],
        postedDate=job.posted_date,
        applicationDeadline=job.application_deadline,
        employerId=str(job.employer_id),
        applicantsCount=job.applicants_count,
        status=job.status.value if hasattr(job.status, "value") else job.status,
        createdAt=job.created_at.isoformat(),
        updatedAt=job.updated_at.isoformat(),
    )


@router.get("", response_model=PaginatedResponse[JobResponse])
async def list_jobs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = None,
    locationType: str | None = None,
    type: str | None = None,
    experienceLevel: str | None = None,
    employerId: str | None = None,
    status: str | None = "active",
    sortBy: str | None = "postedDate",
    sortOrder: str | None = "desc",
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows, total = await job_service.list_jobs(
        db,
        page=page,
        limit=limit,
        search=search,
        location_type=locationType,
        job_type=type,
        experience_level=experienceLevel,
        employer_id=uuid.UUID(employerId) if employerId else None,
        status=status,
        sort_by=sortBy,
        sort_order=sortOrder,
    )
    return PaginatedResponse(
        data=[_job_response(job, company or "") for job, company in rows],
        total=total,
        page=page,
        limit=limit,
        total_pages=math.ceil(total / limit) if total > 0 else 0,
    )


@router.get("/recommended", response_model=SuccessResponse[list[JobResponse]])
async def get_recommended_jobs(
    user: User = Depends(require_role(UserRole.JOB_SEEKER)),
    db: AsyncSession = Depends(get_db),
):
    rows = await job_service.get_recommended(db, user.id)
    return SuccessResponse(data=[_job_response(job, company or "") for job, company in rows])


@router.get("/{job_id}", response_model=SuccessResponse[JobResponse])
async def get_job(
    job_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job, company = await job_service.get_by_id(db, job_id)
    return SuccessResponse(data=_job_response(job, company or ""))


@router.post("", status_code=201, response_model=SuccessResponse[JobResponse])
async def create_job(
    payload: JobCreate,
    employer: User = Depends(require_role(UserRole.EMPLOYER)),
    db: AsyncSession = Depends(get_db),
):
    job = await job_service.create(db, employer, payload)
    company = await job_service.get_employer_company_name(db, employer.id)
    return SuccessResponse(data=_job_response(job, company))


@router.patch("/{job_id}", response_model=SuccessResponse[JobResponse])
async def update_job(
    job_id: uuid.UUID,
    payload: JobUpdate,
    employer: User = Depends(require_role(UserRole.EMPLOYER)),
    db: AsyncSession = Depends(get_db),
):
    job, company = await job_service.update(db, job_id, employer.id, payload)
    return SuccessResponse(data=_job_response(job, company or ""))


@router.delete("/{job_id}", status_code=200)
async def delete_job(
    job_id: uuid.UUID,
    employer: User = Depends(require_role(UserRole.EMPLOYER)),
    db: AsyncSession = Depends(get_db),
):
    await job_service.delete(db, job_id, employer.id)
    return {"message": "Job closed"}


@router.post("/{job_id}/bookmark", response_model=SuccessResponse[dict])
async def toggle_bookmark(
    job_id: uuid.UUID,
    user: User = Depends(require_role(UserRole.JOB_SEEKER)),
    db: AsyncSession = Depends(get_db),
):
    bookmarked = await job_service.toggle_bookmark(db, user.id, job_id)
    return SuccessResponse(data={"bookmarked": bookmarked})
