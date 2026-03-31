import uuid

from sqlalchemy import Enum as SAEnum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import InterviewStatus, InterviewType
from app.db.base import Base, TimestampMixin


class Interview(TimestampMixin, Base):
    __tablename__ = "interviews"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    applicant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_title: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    applicant_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    scheduled_date: Mapped[str] = mapped_column(String(30), nullable=False)
    scheduled_time: Mapped[str] = mapped_column(String(20), nullable=False)
    duration: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[InterviewStatus] = mapped_column(
        SAEnum(InterviewStatus, native_enum=False),
        default=InterviewStatus.SCHEDULED,
        nullable=False,
    )
    type: Mapped[InterviewType] = mapped_column(SAEnum(InterviewType, native_enum=False), nullable=False)
    meeting_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # AI interview data stored as JSONB
    questions: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    responses: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    evaluation: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    application: Mapped["Application"] = relationship(back_populates="interviews", lazy="noload")  # noqa: F821
