from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.incident import Incident
from app.models.monitor import Monitor


def _open_incident_for_monitor(db: Session, monitor_id: int) -> Incident | None:
    stmt = (
        select(Incident)
        .where(Incident.monitor_id == monitor_id, Incident.status == "open")
        .order_by(Incident.started_at.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def build_incident_summary(
    monitor: Monitor,
    status_code: int | None,
    error_message: str | None,
    consecutive_failures: int,
) -> str:
    detail = error_message or "unknown error"
    if status_code is not None:
        detail = f"HTTP {status_code}"
    return (
        f"The endpoint {monitor.url} failed {consecutive_failures} consecutive checks. "
        f"Last observed: {detail}. Detected by CheckStack."
    )


def maybe_create_incident(
    db: Session,
    monitor: Monitor,
    status_code: int | None,
    error_message: str | None,
) -> Incident | None:
    if monitor.consecutive_failures < monitor.failure_threshold:
        return None
    if _open_incident_for_monitor(db, monitor.id):
        return None
    title = f"Incident: {monitor.name} unavailable"
    summary = build_incident_summary(monitor, status_code, error_message, monitor.consecutive_failures)
    incident = Incident(
        monitor_id=monitor.id,
        title=title,
        summary=summary,
        status="open",
        detected_by="CheckStack",
    )
    db.add(incident)
    db.flush()
    return incident


def resolve_open_incidents(db: Session, monitor_id: int) -> int:
    stmt = select(Incident).where(Incident.monitor_id == monitor_id, Incident.status == "open")
    rows = db.execute(stmt).scalars().all()
    now = datetime.now(UTC)
    for inc in rows:
        inc.status = "resolved"
        inc.resolved_at = now
    return len(rows)
