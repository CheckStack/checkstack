from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.check_result import CheckResult


def _start_for_range(now: datetime, r: str) -> datetime:
    r = (r or "24h").lower()
    if r in ("1h", "1H"):
        return now - timedelta(hours=1)
    if r in ("24h", "24H"):
        return now - timedelta(hours=24)
    if r in ("7d", "7D"):
        return now - timedelta(days=7)
    if r in ("30d", "30D"):
        return now - timedelta(days=30)
    raise ValueError("invalid range. Use: 1h, 24h, 7d, 30d")


def get_uptime_series(
    session: Session,
    monitor_id: int,
    range_key: str,
) -> dict[str, Any]:
    now = datetime.now(UTC)
    start = _start_for_range(now, range_key)
    q = (
        select(CheckResult.id, CheckResult.ok, CheckResult.latency_ms, CheckResult.checked_at, CheckResult.status_code)
        .where(CheckResult.monitor_id == monitor_id, CheckResult.checked_at >= start)
        .order_by(CheckResult.checked_at.asc())
    )
    raw = session.execute(q).all()
    points: list[dict] = []
    for _i, ok, lat, checked, code in raw:
        points.append(
            {
                "t": checked,
                "status": "success" if ok else "failure",
                "ok": bool(ok),
                "response_time_ms": lat,
                "status_code": code,
            }
        )
    return {
        "monitor_id": monitor_id,
        "range": (range_key or "24h").lower(),
        "from": start,
        "to": now,
        "points": points,
    }
