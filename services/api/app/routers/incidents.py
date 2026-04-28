from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.incident import Incident
from app.models.monitor import Monitor
from app.models.uptime_log import UptimeLog
from app.schemas.monitor import IncidentDetailRead, IncidentRead
from app.services.alert_service import send_incident_resolved_alert

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("", response_model=list[IncidentRead])
def list_incidents(db: Session = Depends(get_db)) -> list[Incident]:
    return db.query(Incident).order_by(Incident.started_at.desc()).limit(200).all()


@router.get("/{incident_id}", response_model=IncidentDetailRead)
def get_incident(incident_id: int, db: Session = Depends(get_db)) -> IncidentDetailRead:
    i = db.get(Incident, incident_id)
    if not i:
        raise HTTPException(404, "not found")
    m = db.get(Monitor, i.monitor_id)
    if not m:
        raise HTTPException(404, "not found")
    window_end = i.resolved_at or datetime.now(timezone.utc)
    logs_stmt = (
        select(
            UptimeLog.checked_at,
            UptimeLog.status,
            UptimeLog.response_time_ms,
            UptimeLog.error_message,
        )
        .where(
            UptimeLog.monitor_id == i.monitor_id,
            UptimeLog.checked_at >= i.started_at,
            UptimeLog.checked_at <= window_end,
        )
        .order_by(UptimeLog.checked_at.desc())
        .limit(20)
    )
    log_rows = db.execute(logs_stmt).all()

    reason_stmt = (
        select(UptimeLog.error_message, func.count(UptimeLog.id).label("failures"))
        .where(
            UptimeLog.monitor_id == i.monitor_id,
            UptimeLog.checked_at >= i.started_at,
            UptimeLog.checked_at <= window_end,
            UptimeLog.status == "DOWN",
            UptimeLog.error_message.is_not(None),
            UptimeLog.error_message != "",
        )
        .group_by(UptimeLog.error_message)
        .order_by(func.count(UptimeLog.id).desc(), UptimeLog.error_message.asc())
        .limit(1)
    )
    failure_reason = db.execute(reason_stmt).first()
    duration_seconds = None
    if i.resolved_at is not None:
        duration_seconds = int((i.resolved_at - i.started_at).total_seconds())

    return IncidentDetailRead(
        id=i.id,
        monitor_id=i.monitor_id,
        title=i.title,
        summary=i.summary,
        status=i.status,
        detected_by=i.detected_by,
        started_at=i.started_at,
        resolved_at=i.resolved_at,
        duration_seconds=duration_seconds,
        start_time=i.started_at,
        end_time=i.resolved_at,
        monitor_name=m.name,
        monitor_url=m.url,
        monitor={
            "id": m.id,
            "name": m.name,
            "url": m.url,
            "alerts_enabled": bool(m.alerts_enabled),
        },
        failure_reason_summary=failure_reason[0] if failure_reason else None,
        uptime_logs=[
            {
                "timestamp": row[0],
                "status": row[1],
                "response_time_ms": row[2],
                "error_message": row[3],
            }
            for row in log_rows
        ],
    )


@router.post("/{incident_id}/resolve", response_model=IncidentRead)
async def resolve_incident(incident_id: int, db: Session = Depends(get_db)) -> Incident:
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(404, detail="not found")
    if incident.status == "resolved":
        return incident
    now = datetime.now(timezone.utc)
    incident.status = "resolved"
    incident.resolved_at = now
    if incident.started_at:
        incident.duration_seconds = int((now - incident.started_at).total_seconds())
    db.add(incident)
    db.commit()
    db.refresh(incident)
    monitor = db.get(Monitor, incident.monitor_id)
    if monitor is not None:
        await send_incident_resolved_alert(db, incident, monitor)
    return incident
