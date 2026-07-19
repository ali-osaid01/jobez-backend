import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.models.notification import Notification


class NotificationService:
    async def create(
        self,
        db: AsyncSession,
        *,
        recipient_id: uuid.UUID,
        title: str,
        message: str,
        type: str = "info",
        data: dict | None = None,
    ) -> Notification:
        notification = Notification(
            id=uuid.uuid4(),
            recipient_id=recipient_id,
            title=title,
            message=message,
            type=type,
            data=data,
        )
        db.add(notification)
        await db.flush()
        return notification

    async def list_for_user(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        page: int = 1,
        limit: int = 20,
        unread_only: bool = False,
    ) -> tuple[list[Notification], int, int]:
        stmt = select(Notification).where(Notification.recipient_id == user_id)
        if unread_only:
            stmt = stmt.where(Notification.read_at.is_(None))

        total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        unread_count = (
            await db.execute(
                select(func.count()).select_from(Notification).where(
                    Notification.recipient_id == user_id,
                    Notification.read_at.is_(None),
                )
            )
        ).scalar_one()

        result = await db.execute(
            stmt.order_by(Notification.created_at.desc()).offset((page - 1) * limit).limit(limit)
        )
        return list(result.scalars().all()), total, unread_count

    async def mark_read(self, db: AsyncSession, *, notification_id: uuid.UUID, user_id: uuid.UUID) -> Notification:
        notification = (
            await db.execute(
                select(Notification).where(Notification.id == notification_id, Notification.recipient_id == user_id)
            )
        ).scalar_one_or_none()
        if not notification:
            raise NotFoundException("Notification")
        if notification.read_at is None:
            notification.read_at = datetime.now(timezone.utc)
            await db.flush()
        return notification

    async def mark_all_read(self, db: AsyncSession, *, user_id: uuid.UUID) -> None:
        await db.execute(
            update(Notification)
            .where(Notification.recipient_id == user_id, Notification.read_at.is_(None))
            .values(read_at=datetime.now(timezone.utc))
        )
        await db.flush()


notification_service = NotificationService()
