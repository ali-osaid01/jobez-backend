"""change date fields from string to date

Revision ID: b7f3a1c92e45
Revises: 1fa07e0b34e7
Create Date: 2026-03-28 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7f3a1c92e45"
down_revision: Union[str, None] = "1fa07e0b34e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "jobs",
        "posted_date",
        type_=sa.Date(),
        postgresql_using="posted_date::date",
        nullable=False,
    )
    op.alter_column(
        "jobs",
        "application_deadline",
        type_=sa.Date(),
        postgresql_using="application_deadline::date",
        nullable=True,
    )
    op.alter_column(
        "applications",
        "applied_date",
        type_=sa.Date(),
        postgresql_using="applied_date::date",
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "jobs",
        "posted_date",
        type_=sa.String(length=30),
        nullable=False,
    )
    op.alter_column(
        "jobs",
        "application_deadline",
        type_=sa.String(length=30),
        nullable=True,
    )
    op.alter_column(
        "applications",
        "applied_date",
        type_=sa.String(length=30),
        nullable=False,
    )
