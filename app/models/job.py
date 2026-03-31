import uuid
from datetime import date

from sqlalchemy import Date, Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ExperienceLevel, JobStatus, JobType, LocationType
from app.db.base import Base, TimestampMixin


class Job(TimestampMixin, Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    employer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    location_type: Mapped[LocationType] = mapped_column(SAEnum(LocationType, native_enum=False), nullable=False)
    salary: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[JobType] = mapped_column(SAEnum(JobType, native_enum=False), nullable=False)
    experience_level: Mapped[ExperienceLevel] = mapped_column(SAEnum(ExperienceLevel, native_enum=False), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    requirements: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    responsibilities: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    benefits: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    posted_date: Mapped[date] = mapped_column(Date, nullable=False)
    application_deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    applicants_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[JobStatus] = mapped_column(SAEnum(JobStatus, native_enum=False), default=JobStatus.ACTIVE, nullable=False)

    employer: Mapped["User"] = relationship(back_populates="posted_jobs", lazy="noload")  # noqa: F821
    applications: Mapped[list["Application"]] = relationship(back_populates="job", lazy="noload")  # noqa: F821
    bookmarks: Mapped[list["Bookmark"]] = relationship(back_populates="job", lazy="noload")  # noqa: F821
