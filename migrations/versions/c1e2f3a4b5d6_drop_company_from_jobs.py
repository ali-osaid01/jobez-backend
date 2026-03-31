"""drop company column from jobs

Revision ID: c1e2f3a4b5d6
Revises: b7f3a1c92e45
Create Date: 2026-03-28 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1e2f3a4b5d6"
down_revision: Union[str, None] = "b7f3a1c92e45"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("jobs", "company")


def downgrade() -> None:
    op.add_column("jobs", sa.Column("company", sa.String(length=255), nullable=True))
