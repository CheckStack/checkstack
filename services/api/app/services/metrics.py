from __future__ import annotations

from datetime import UTC, datetime, timedelta
from math import ceil

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.uptime_log import UptimeLog

_ALLOWED_RANGES: dict[str, timedelta] = {
    "1h": timedelta(hours=1),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
}

_MAX_METRIC_POINTS = 1000


def parse_metrics_range(range_key: str) -> str:
    normalized = (range_key or "24h").lower()
    if normalized not in _ALLOWED_RANGES:
        raise ValueError("range must be one of: 1h, 24h, 7d")
    return normalized


def metrics_range_start(range_key: str, now: datetime | None = None) -> datetime:
    normalized = parse_metrics_range(range_key)
    current = now or datetime.now(UTC)
    return current - _ALLOWED_RANGES[normalized]


def calculate_sla_percent(uptime_checks: int, total_checks: int) -> float:
    if total_checks <= 0:
        return 100.0
    return round((uptime_checks / total_checks) * 100.0, 3)


def fetch_metrics(
    db: Session,
    monitor_id: int,
    range_key: str,
    *,
    max_points: int = _MAX_METRIC_POINTS,
) -> list[dict]:
    start = metrics_range_start(range_key)
    stmt = (
        select(UptimeLog.checked_at, UptimeLog.status, UptimeLog.response_time_ms)
        .where(UptimeLog.monitor_id == monitor_id, UptimeLog.checked_at >= start)
        .order_by(UptimeLog.checked_at.asc())
    )
    rows = db.execute(stmt).all()

    if max_points > 0 and len(rows) > max_points:
        stride = ceil(len(rows) / max_points)
        rows = rows[::stride]

    return [
        {
            "timestamp": checked_at,
            "status": status,
            "response_time_ms": float(response_time_ms or 0.0),
        }
        for checked_at, status, response_time_ms in rows
    ]


def compute_sla_from_uptime_log(db: Session, monitor_id: int, window: str) -> dict:
    start = metrics_range_start(window)
    stmt = select(
        func.count(UptimeLog.id),
        func.sum(case((UptimeLog.status == "UP", 1), else_=0)),
    ).where(UptimeLog.monitor_id == monitor_id, UptimeLog.checked_at >= start)
    total, uptime_checks = db.execute(stmt).one()
    total = int(total or 0)
    uptime_checks = int(uptime_checks or 0)

    return {
        "monitor_id": monitor_id,
        "window": parse_metrics_range(window),
        "uptime_percent": calculate_sla_percent(uptime_checks, total),
        "total_checks": total,
        "successful_checks": uptime_checks,
    }
