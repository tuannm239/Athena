"""Editable investment universe — watchlist_universe table

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-07-21

The runtime-editable set of symbols the sync covers (never hardcoded in
logic). Seeded once with the default universe.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e2f3a4b5c6d7"
down_revision: Union[str, None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "watchlist_universe",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("sector", sa.String(length=64), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("sync_level", sa.String(length=16), nullable=False, server_default="NORMAL"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_watchlist_universe")),
        sa.UniqueConstraint("symbol", name="uq_watchlist_universe_symbol"),
    )
    op.create_index(
        op.f("ix_watchlist_universe_symbol"), "watchlist_universe", ["symbol"], unique=False
    )
    op.create_index(
        op.f("ix_watchlist_universe_sync_level"), "watchlist_universe", ["sync_level"], unique=False
    )
    op.create_index(
        op.f("ix_watchlist_universe_is_active"), "watchlist_universe", ["is_active"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_watchlist_universe_is_active"), table_name="watchlist_universe")
    op.drop_index(op.f("ix_watchlist_universe_sync_level"), table_name="watchlist_universe")
    op.drop_index(op.f("ix_watchlist_universe_symbol"), table_name="watchlist_universe")
    op.drop_table("watchlist_universe")
