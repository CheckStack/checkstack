from datetime import UTC, datetime, timedelta

from sqlalchemy import Integer, cast, func, select
from sqlalchemy.orm import Session

from app.models.check_result import CheckResult


def window_start(window: str, now: datetime | None = None) -> datetime:
    now = now or datetime.now(UTC)
    if window == "24h":
        return now - timedelta(hours=24)
    if window == "7d":
        return now - timedelta(days=7)
    raise ValueError("window must be '24h' or '7d'")


def compute_sla(db: Session, monitor_id: int, window: str) -> dict:
    start = window_start(window)
    stmt = select(
        func.count(CheckResult.id),
        func.sum(cast(CheckResult.ok, Integer)),
    ).where(CheckResult.monitor_id == monitor_id, CheckResult.checked_at >= start)
    total, successes = db.execute(stmt).one()
    total = int(total or 0)
    successes = int(successes or 0)
    uptime = (successes / total * 100.0) if total else 100.0
    return {
        "monitor_id": monitor_id,
        "window": window,
        "uptime_percent": round(uptime, 3),
        "total_checks": total,
        "successful_checks": successes,
    }
