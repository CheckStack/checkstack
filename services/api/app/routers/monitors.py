from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.check_result import CheckResult
from app.models.monitor import Monitor
from app.schemas.monitor import CheckResultRead, MonitorCreate, MonitorRead, SlaResponse
from app.services.sla import compute_sla

router = APIRouter(prefix="/monitors", tags=["monitors"])


@router.post("", response_model=MonitorRead)
def create_monitor(payload: MonitorCreate, db: Session = Depends(get_db)) -> Monitor:
    monitor = Monitor(
        name=payload.name,
        url=str(payload.url),
        interval_seconds=payload.interval_seconds,
        timeout_seconds=payload.timeout_seconds,
        failure_threshold=payload.failure_threshold,
    )
    db.add(monitor)
    db.commit()
    db.refresh(monitor)
    return monitor


@router.get("", response_model=list[MonitorRead])
def list_monitors(db: Session = Depends(get_db)) -> list[Monitor]:
    return db.query(Monitor).order_by(Monitor.id.asc()).all()


@router.get("/{monitor_id}", response_model=MonitorRead)
def get_monitor(monitor_id: int, db: Session = Depends(get_db)) -> Monitor:
    monitor = db.get(Monitor, monitor_id)
    if not monitor:
        raise HTTPException(status_code=404, detail="monitor not found")
    return monitor


@router.delete("/{monitor_id}", status_code=204)
def delete_monitor(monitor_id: int, db: Session = Depends(get_db)) -> None:
    monitor = db.get(Monitor, monitor_id)
    if not monitor:
        raise HTTPException(status_code=404, detail="monitor not found")
    db.delete(monitor)
    db.commit()


@router.get("/{monitor_id}/checks", response_model=list[CheckResultRead])
def list_checks(
    monitor_id: int,
    db: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[CheckResult]:
    monitor = db.get(Monitor, monitor_id)
    if not monitor:
        raise HTTPException(status_code=404, detail="monitor not found")
    return (
        db.query(CheckResult)
        .filter(CheckResult.monitor_id == monitor_id)
        .order_by(CheckResult.checked_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/{monitor_id}/sla", response_model=SlaResponse)
def get_sla(monitor_id: int, window: str = Query(default="24h"), db: Session = Depends(get_db)) -> dict:
    monitor = db.get(Monitor, monitor_id)
    if not monitor:
        raise HTTPException(status_code=404, detail="monitor not found")
    if window not in ("24h", "7d"):
        raise HTTPException(status_code=400, detail="window must be 24h or 7d")
    return compute_sla(db, monitor_id, window)
