from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.enums import UserRole
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.services.dashboard_service import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=SuccessResponse[dict])
async def get_dashboard_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role == UserRole.JOB_SEEKER:
        stats = await dashboard_service.get_job_seeker_stats(db, user)
    else:
        stats = await dashboard_service.get_employer_stats(db, user)

    return SuccessResponse(data=stats)
