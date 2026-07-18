"""Pilot daily report generator (Phase 5, W6).

Operational tooling — reads the decision + audit tables for a given day and
writes a Markdown + JSON report to the pilot report directory. It is
read-only (SELECT only), does NOT touch business logic, and produces the
retained daily record required by Pilot Mode.

Run:  python -m scripts.daily_report [YYYY-MM-DD]
Env:  DATABASE_URL, ATHENA_PILOT_REPORT_DIR (default: data/pilot-reports)
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from infrastructure.db.models import AuditRow, DecisionRow


def generate_report(sessions: sessionmaker[Session], day: date) -> dict[str, Any]:
    """Build the daily pilot report payload for `day` (UTC)."""
    start = datetime.combine(day, time.min, tzinfo=timezone.utc)
    end = start + timedelta(days=1)

    with sessions() as session:
        # decisions created that day, by status
        created = session.execute(
            select(DecisionRow.status, func.count())
            .where(DecisionRow.created_at >= start, DecisionRow.created_at < end)
            .group_by(DecisionRow.status)
        ).all()
        created_by_status = {row[0]: row[1] for row in created}

        # lifetime totals by status (portfolio-wide posture)
        totals = session.execute(
            select(DecisionRow.status, func.count()).group_by(DecisionRow.status)
        ).all()
        totals_by_status = {row[0]: row[1] for row in totals}

        # audit events that day (entity_type:action), plus the snapshot so we
        # can read the status a decision transitioned into. Human review is an
        # UPDATE on a decision whose snapshot status is APPROVED / REJECTED
        # (see SqlDecisionRepository.save + DecisionStatus).
        audit = session.execute(
            select(AuditRow.entity_type, AuditRow.action, AuditRow.snapshot).where(
                AuditRow.created_at >= start, AuditRow.created_at < end
            )
        ).all()
        audit_actions = Counter(f"{row[0]}:{row[1]}" for row in audit)

        approvals = 0
        rejections = 0
        for entity_type, action, snapshot in audit:
            if entity_type != "decision" or action != "UPDATE":
                continue
            status = (snapshot or {}).get("status")
            if status == "APPROVED":
                approvals += 1
            elif status == "REJECTED":
                rejections += 1

    return {
        "report_date": day.isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pilot_mode": True,
        "order_execution": False,  # structural guarantee
        "decisions_created_today": sum(created_by_status.values()),
        "decisions_created_by_status": created_by_status,
        "reviews_today": {"approved": approvals, "rejected": rejections},
        "lifetime_decisions_by_status": totals_by_status,
        "audit_events_today": dict(audit_actions),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# Athena Pilot Daily Report — {report['report_date']}",
        "",
        f"Generated: {report['generated_at']} · Pilot mode: **ON** · "
        "Order execution: **DISABLED** (decision-support only)",
        "",
        "## Decisions created today",
        f"- Total: **{report['decisions_created_today']}**",
    ]
    for status, n in sorted(report["decisions_created_by_status"].items()):
        lines.append(f"  - {status}: {n}")
    lines += [
        "",
        "## Human review activity today",
        f"- Approved: {report['reviews_today']['approved']}",
        f"- Rejected: {report['reviews_today']['rejected']}",
        "",
        "## Lifetime decisions by status",
    ]
    for status, n in sorted(report["lifetime_decisions_by_status"].items()):
        lines.append(f"- {status}: {n}")
    lines += ["", "## Audit events today"]
    if report["audit_events_today"]:
        for action, n in sorted(report["audit_events_today"].items()):
            lines.append(f"- `{action}`: {n}")
    else:
        lines.append("- (none)")
    lines += [
        "",
        "---",
        "_Athena generates Decision Objects only. Every decision requires human "
        "approval; no trades are executed and no broker is connected._",
    ]
    return "\n".join(lines) + "\n"


def write_report(report: dict[str, Any], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = report["report_date"]
    json_path = out_dir / f"pilot-report-{stem}.json"
    md_path = out_dir / f"pilot-report-{stem}.md"
    json_path.write_text(json.dumps(report, indent=2))
    md_path.write_text(render_markdown(report))
    return json_path, md_path


def main() -> None:
    from infrastructure.config import Settings
    from infrastructure.db.engine import build_engine, build_session_factory

    day = (
        date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else datetime.now(timezone.utc).date()
    )
    settings = Settings.from_env()
    sessions = build_session_factory(build_engine(settings))
    report = generate_report(sessions, day)
    out_dir = Path(os.environ.get("ATHENA_PILOT_REPORT_DIR", "data/pilot-reports"))
    json_path, md_path = write_report(report, out_dir)
    print(f"pilot report for {day} -> {md_path} , {json_path}")
    print(
        f"  decisions created: {report['decisions_created_today']} · "
        f"approved: {report['reviews_today']['approved']} · "
        f"rejected: {report['reviews_today']['rejected']}"
    )


if __name__ == "__main__":
    main()
