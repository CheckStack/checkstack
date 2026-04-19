from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.check_result import CheckResult


def _window_start(window: str, now: datetime) -> datetime:
    if window == "24h":
        return now - timedelta(hours=24)
    if window == "7d":
        return now - timedelta(days=7)
    raise ValueError("window must be 24h or 7d")


def _p95(sample: list[float]) -> float | None:
    if not sample:
        return None
    s = sorted(sample)
    idx = int(round(0.95 * (len(s) - 1)))
    return float(s[idx])


def compute_latency_stats(
    session: Session,
    monitor_id: int,
    window: str,
    now: datetime | None = None,
) -> dict:
    now = now or datetime.now(UTC)
    start = _window_start(window, now)
    stmt = (
        select(CheckResult.id, CheckResult.ok, CheckResult.latency_ms)
        .where(
            CheckResult.monitor_id == monitor_id,
            CheckResult.checked_at >= start,
        )
        .order_by(CheckResult.checked_at.asc())
    )
    rows = session.execute(stmt).all()
    lats: list[float] = []
    for _id, ok, lat in rows:
        if lat is not None and (ok is True or ok is not None):
            lats.append(float(lat))
    total = len(rows)
    nlat = len(lats)
    avg: float | None
    p95: float | None
    if lats:
        s = sum(lats)
        avg = round(s / nlat, 2)
        p95r = _p95(lats)
        p95 = round(p95r, 2) if p95r is not None else None
    else:
        avg = p95 = None
    if lats:
        mmin, mmax = min(lats), max(lats)
    else:
        mmin, mmax = None, None
    return {
        "monitor_id": monitor_id,
        "window": window,
        "avg_latency_ms": avg,
        "p95_latency_ms": p95,
        "min_latency_ms": round(mmin, 2) if mmin is not None else None,
        "max_latency_ms": round(mmax, 2) if mmax is not None else None,
        "total_checks": total,
        "with_latency": nlat,
    }
