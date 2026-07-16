"""ADR-0006 evidence model and companies table (Executive Directive)

Revision ID: b5c6d7e8f9a0
Revises: 7aad5a7b7385
Create Date: 2026-07-16

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from infrastructure.db.base import PortableJSON

revision: str = "b5c6d7e8f9a0"
down_revision: Union[str, None] = "7aad5a7b7385"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("evidence", "kind", new_column_name="direction")
    op.alter_column("evidence", "confidence", new_column_name="reliability")
    op.alter_column("evidence", "description", new_column_name="explanation")
    op.add_column("evidence", sa.Column("metadata_json", PortableJSON, nullable=True))
    op.execute("UPDATE evidence SET direction = 'CONTRADICTING' WHERE direction = 'COUNTER'")

    op.create_table(
        "companies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("exchange", sa.String(length=32), nullable=False),
        sa.Column("sector", sa.String(length=128), nullable=False),
        sa.Column("industry", sa.String(length=128), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_companies")),
    )
    op.create_index(op.f("ix_companies_created_at"), "companies", ["created_at"], unique=False)
    op.create_index(op.f("ix_companies_ticker"), "companies", ["ticker"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_companies_ticker"), table_name="companies")
    op.drop_index(op.f("ix_companies_created_at"), table_name="companies")
    op.drop_table("companies")
    op.execute("UPDATE evidence SET direction = 'COUNTER' WHERE direction = 'CONTRADICTING'")
    op.drop_column("evidence", "metadata_json")
    op.alter_column("evidence", "explanation", new_column_name="description")
    op.alter_column("evidence", "reliability", new_column_name="confidence")
    op.alter_column("evidence", "direction", new_column_name="kind")
