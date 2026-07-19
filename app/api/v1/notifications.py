import math
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.notification import Notification
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.notification import NotificationListResponse, NotificationResponse
from app.services.notification_service import notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def _notification_response(notification: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=str(notification.id),
        title=notification.title,
        message=notification.message,
        type=notification.type,
        data=notification.data,
        readAt=notification.read_at,
        createdAt=notification.created_at,
    )


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    unreadOnly: bool = False,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    notifications, total, unread_count = await notification_service.list_for_user(
        db,
        user_id=user.id,
        page=page,
        limit=limit,
        unread_only=unreadOnly,
    )
    return NotificationListResponse(
        data=[_notification_response(notification) for notification in notifications],
        total=total,
        page=page,
        limit=limit,
        total_pages=math.ceil(total / limit) if total > 0 else 0,
        unreadCount=unread_count,
    )


@router.post("/{notification_id}/read", response_model=SuccessResponse[NotificationResponse])
async def mark_notification_read(
    notification_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    notification = await notification_service.mark_read(db, notification_id=notification_id, user_id=user.id)
    return SuccessResponse(data=_notification_response(notification))


@router.post("/read-all")
async def mark_all_notifications_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await notification_service.mark_all_read(db, user_id=user.id)
    return {"message": "Notifications marked read"}
