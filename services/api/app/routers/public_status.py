from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.incident import Incident
from app.models.monitor import Monitor
from app.services.sla import compute_sla

router = APIRouter(prefix="/public", tags=["public"])
status_router = APIRouter(prefix="/status", tags=["public"])


@router.get("/status", response_model=dict)
def public_status(db: Session = Depends(get_db)) -> dict:
    out: list[dict] = []
    for m in db.query(Monitor).filter(Monitor.is_public == True).order_by(Monitor.id).all():  # noqa: E712
        s24 = compute_sla(db, m.id, "24h")
        out.append(
            {
                "id": m.id,
                "name": m.name,
                "url": m.url,
                "status": m.last_status or "unknown",
                "sla_24h_percent": s24["uptime_percent"],
            }
        )
    return {"monitors": out}


@status_router.get("/{slug}", response_model=dict)
def get_public_monitor_status(slug: str, response: Response, db: Session = Depends(get_db)) -> dict:
    monitor = (
        db.query(Monitor)
        .filter(Monitor.public_slug == slug, Monitor.is_public == True)  # noqa: E712
        .one_or_none()
    )
    if monitor is None:
        raise HTTPException(status_code=404, detail="status page not found")

    recent_incidents = (
        db.query(Incident)
        .filter(Incident.monitor_id == monitor.id)
        .order_by(Incident.started_at.desc())
        .limit(5)
        .all()
    )

    sla_24h = compute_sla(db, monitor.id, "24h")

    response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"
    latest_change = monitor.last_checked_at or monitor.created_at
    if recent_incidents:
        latest_incident_ts = recent_incidents[0].resolved_at or recent_incidents[0].started_at
        if latest_incident_ts and latest_incident_ts > latest_change:
            latest_change = latest_incident_ts
    response.headers["ETag"] = f'W/"{monitor.id}:{int(latest_change.timestamp())}"'

    return {
        "name": monitor.name,
        "current_status": monitor.last_status or "unknown",
        "uptime_24h_percent": sla_24h["uptime_percent"],
        "recent_incidents": [
            {
                "id": i.id,
                "title": i.title,
                "status": i.status,
                "started_at": i.started_at,
                "resolved_at": i.resolved_at,
                "duration_seconds": i.duration_seconds,
            }
            for i in recent_incidents
        ],
        "generated_at": datetime.now(timezone.utc),
        "powered_by": "CheckStack",
    }
