from datetime import datetime

from app.schemas.common import PaginatedResponse
from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: str
    title: str
    message: str
    type: str
    data: dict | None = None
    readAt: datetime | None = None
    createdAt: datetime


class NotificationListResponse(PaginatedResponse[NotificationResponse]):
    unreadCount: int
