"""Persisted company fundamentals read-model — company_fundamentals

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-07-21

One JSON payload per ticker (ratios + explainable scores + YoY growth),
refreshed by the company sync and read by the company API.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "f3a4b5c6d7e8"
down_revision: Union[str, None] = "e2f3a4b5c6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_JSON = sa.JSON().with_variant(JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "company_fundamentals",
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("payload", _JSON, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("ticker", name=op.f("pk_company_fundamentals")),
    )


def downgrade() -> None:
    op.drop_table("company_fundamentals")
