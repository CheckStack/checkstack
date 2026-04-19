from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.incident import Incident
from app.schemas.monitor import IncidentRead

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("", response_model=list[IncidentRead])
def list_incidents(db: Session = Depends(get_db)) -> list[Incident]:
    return db.query(Incident).order_by(Incident.started_at.desc()).limit(200).all()


@router.post("/{incident_id}/resolve", response_model=IncidentRead)
def resolve_incident(incident_id: int, db: Session = Depends(get_db)) -> Incident:
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="incident not found")
    if incident.status == "resolved":
        return incident
    incident.status = "resolved"
    incident.resolved_at = datetime.now(UTC)
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident
