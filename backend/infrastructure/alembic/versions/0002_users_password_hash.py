"""users.password_hash for JWT authentication (ADR-0009)

Revision ID: a1b2c3d4e5f6
Revises: ec77f528e384
Create Date: 2026-07-15

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "ec77f528e384"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(length=256), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "password_hash")
