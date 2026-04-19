from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.incident import Incident
from app.models.monitor import Monitor
from app.schemas.monitor import IncidentDetailRead, IncidentRead

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
    return IncidentDetailRead(
        id=i.id,
        monitor_id=i.monitor_id,
        title=i.title,
        summary=i.summary,
        status=i.status,
        detected_by=i.detected_by,
        started_at=i.started_at,
        resolved_at=i.resolved_at,
        duration_seconds=i.duration_seconds,
        start_time=i.started_at,
        end_time=i.resolved_at,
        monitor_name=m.name,
        monitor_url=m.url,
    )


@router.post("/{incident_id}/resolve", response_model=IncidentRead)
def resolve_incident(incident_id: int, db: Session = Depends(get_db)) -> Incident:
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(404, detail="not found")
    if incident.status == "resolved":
        return incident
    now = datetime.now(UTC)
    incident.status = "resolved"
    incident.resolved_at = now
    if incident.started_at:
        incident.duration_seconds = int((now - incident.started_at).total_seconds())
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident
