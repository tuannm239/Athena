"""Lineage reference — the reproducibility tuple every artifact must carry."""

from __future__ import annotations

from dataclasses import dataclass

from .identifiers import RunId, SnapshotId


@dataclass(frozen=True, slots=True)
class Lineage:
    run_id: RunId
    snapshot_id: SnapshotId
