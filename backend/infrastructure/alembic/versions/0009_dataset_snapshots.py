"""Durable SQL snapshot store — dataset_snapshots table

Revision ID: d1e2f3a4b5c6
Revises: c9d0e1f2a3b4
Create Date: 2026-07-20

Backs the SQL snapshot store (SnapshotStore port) so published Data Pipeline
snapshots survive restarts / ephemeral disks. Each (snapshot_id, table_name)
holds one polars frame serialised as Parquet bytes; the unique constraint
enforces immutability.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dataset_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_id", sa.String(length=128), nullable=False),
        sa.Column("table_name", sa.String(length=128), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dataset_snapshots")),
        sa.UniqueConstraint("snapshot_id", "table_name", name="uq_dataset_snapshots_id_table"),
    )
    op.create_index(
        op.f("ix_dataset_snapshots_snapshot_id"),
        "dataset_snapshots",
        ["snapshot_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_dataset_snapshots_snapshot_id"), table_name="dataset_snapshots")
    op.drop_table("dataset_snapshots")
