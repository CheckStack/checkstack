from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
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
    open_after = max(1, int(settings.incident_open_after_failures))
    if monitor.consecutive_failures < open_after:
        return None
    now = datetime.now(UTC)
    debounce = max(0, int(settings.incident_debounce_seconds))
    if monitor.last_incident_resolved_at is not None and debounce > 0:
        elapsed = (now - monitor.last_incident_resolved_at).total_seconds()
        if elapsed < debounce:
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
    monitor.last_incident_opened_at = now
    db.add(incident)
    db.flush()
    return incident


def resolve_open_incidents(db: Session, monitor: Monitor) -> int:
    close_after = max(1, int(settings.incident_close_after_successes))
    if monitor.consecutive_successes < close_after:
        return 0

    now = datetime.now(UTC)
    debounce = max(0, int(settings.incident_debounce_seconds))
    if monitor.last_incident_opened_at is not None and debounce > 0:
        elapsed = (now - monitor.last_incident_opened_at).total_seconds()
        if elapsed < debounce:
            return 0

    stmt = select(Incident).where(Incident.monitor_id == monitor.id, Incident.status == "open")
    rows = db.execute(stmt).scalars().all()
    if not rows:
        return 0
    for inc in rows:
        inc.status = "resolved"
        inc.resolved_at = now
        if inc.started_at:
            inc.duration_seconds = int((now - inc.started_at).total_seconds())
    monitor.last_incident_resolved_at = now
    return len(rows)
