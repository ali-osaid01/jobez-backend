import uuid

from sqlalchemy import Boolean, Enum as SAEnum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import UserRole
from app.db.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole, native_enum=False), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    refresh_token_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    profile: Mapped["Profile"] = relationship(back_populates="user", uselist=False, lazy="noload")  # noqa: F821
    posted_jobs: Mapped[list["Job"]] = relationship(back_populates="employer", lazy="noload")  # noqa: F821
    applications: Mapped[list["Application"]] = relationship(back_populates="applicant", lazy="noload")  # noqa: F821
    bookmarks: Mapped[list["Bookmark"]] = relationship(back_populates="user", lazy="noload")  # noqa: F821
