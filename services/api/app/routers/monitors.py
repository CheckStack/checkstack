from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.check_result import CheckResult
from app.models.monitor import Monitor
from app.models.tag import Tag
from app.schemas.monitor import (
    CheckResultRead,
    MonitorCreate,
    MonitorRead,
    MonitorUpdate,
    MonitorMetricPoint,
    SlaResponse,
)
from app.routers.serializers import load_monitors_eager, to_monitor_read
from app.services.latency_stats import compute_latency_stats
from app.services.metrics import fetch_metrics, parse_metrics_range
from app.services.sla import compute_sla

router = APIRouter(prefix="/monitors", tags=["monitors"])


@router.post("", response_model=MonitorRead)
def create_monitor(payload: MonitorCreate, db: Session = Depends(get_db)) -> MonitorRead:
    monitor = Monitor(
        name=payload.name,
        url=str(payload.url),
        interval_seconds=payload.interval_seconds,
        timeout_seconds=payload.timeout_seconds,
        failure_threshold=payload.failure_threshold,
        alerts_enabled=payload.alerts_enabled,
    )
    db.add(monitor)
    db.flush()
    if payload.tag_ids:
        tags = db.query(Tag).filter(Tag.id.in_(set(payload.tag_ids))).all()
        if len(tags) != len(set(payload.tag_ids)):
            raise HTTPException(status_code=400, detail="one or more tag_ids not found")
        monitor.tags = tags
    db.commit()
    db.refresh(monitor)
    m2 = (
        db.query(Monitor)
        .options(joinedload(Monitor.tags))
        .filter(Monitor.id == monitor.id)
        .one()
    )
    return to_monitor_read(db, m2)


@router.get("", response_model=list[MonitorRead])
def list_monitors(
    tag_id: int | None = Query(default=None, description="filter by tag"),
    db: Session = Depends(get_db),
) -> list[MonitorRead]:
    if tag_id is not None:
        mlist = (
            db.query(Monitor)
            .options(joinedload(Monitor.tags))
            .join(Monitor.tags)
            .filter(Tag.id == tag_id)
            .order_by(Monitor.id)
            .distinct()
            .all()
        )
    else:
        mlist = load_monitors_eager(db)
    return [to_monitor_read(db, m) for m in mlist]


@router.get("/{monitor_id}/stats", response_model=dict)
def get_monitor_stats(
    monitor_id: int,
    window: str = Query(default="24h", pattern="^(24h|7d)$"),
    db: Session = Depends(get_db),
) -> dict:
    monitor = db.get(Monitor, monitor_id)
    if not monitor:
        raise HTTPException(status_code=404, detail="monitor not found")
    l = compute_latency_stats(db, monitor_id, window)
    s = compute_sla(db, monitor_id, window)
    return {**l, "sla": s}


@router.patch("/{monitor_id}", response_model=MonitorRead)
def update_monitor(
    monitor_id: int, payload: MonitorUpdate, db: Session = Depends(get_db)
) -> MonitorRead:
    m = (
        db.query(Monitor)
        .options(joinedload(Monitor.tags))
        .filter(Monitor.id == monitor_id)
        .one_or_none()
    )
    if not m:
        raise HTTPException(status_code=404, detail="monitor not found")
    d = payload.model_dump(exclude_unset=True)
    tids = d.pop("tag_ids", None)
    for k, v in d.items():
        setattr(m, k, v)
    if tids is not None:
        tags = db.query(Tag).filter(Tag.id.in_(tids)).all()
        if len(tags) != len(set(tids)):
            raise HTTPException(status_code=400, detail="one or more tag_ids not found")
        m.tags = tags
    db.add(m)
    db.commit()
    m2 = (
        db.query(Monitor)
        .options(joinedload(Monitor.tags))
        .filter(Monitor.id == monitor_id)
        .one()
    )
    return to_monitor_read(db, m2)


@router.get("/{monitor_id}", response_model=MonitorRead)
def get_monitor(monitor_id: int, db: Session = Depends(get_db)) -> MonitorRead:
    m = (
        db.query(Monitor)
        .options(joinedload(Monitor.tags))
        .filter(Monitor.id == monitor_id)
        .one_or_none()
    )
    if not m:
        raise HTTPException(status_code=404, detail="monitor not found")
    return to_monitor_read(db, m)


@router.delete("/{monitor_id}", status_code=204)
def delete_monitor(monitor_id: int, db: Session = Depends(get_db)) -> None:
    m = db.get(Monitor, monitor_id)
    if not m:
        raise HTTPException(status_code=404, detail="monitor not found")
    db.delete(m)
    db.commit()


@router.get("/{monitor_id}/checks", response_model=list[CheckResultRead])
def list_checks(
    monitor_id: int,
    db: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[CheckResult]:
    m = db.get(Monitor, monitor_id)
    if not m:
        raise HTTPException(status_code=404, detail="monitor not found")
    return (
        db.query(CheckResult)
        .filter(CheckResult.monitor_id == monitor_id)
        .order_by(CheckResult.checked_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/{monitor_id}/metrics", response_model=list[MonitorMetricPoint])
def get_monitor_metrics(
    monitor_id: int,
    time_range: str = Query(default="24h", alias="range", pattern="^(1h|24h|7d)$"),
    db: Session = Depends(get_db),
) -> list[dict]:
    monitor = db.get(Monitor, monitor_id)
    if not monitor:
        raise HTTPException(status_code=404, detail="monitor not found")
    normalized_range = parse_metrics_range(time_range)
    return fetch_metrics(db, monitor_id, normalized_range)


@router.get("/{monitor_id}/sla", response_model=SlaResponse)
def get_sla(monitor_id: int, window: str = Query(default="24h"), db: Session = Depends(get_db)) -> dict:
    m = db.get(Monitor, monitor_id)
    if not m:
        raise HTTPException(status_code=404, detail="monitor not found")
    if window not in ("1h", "24h", "7d"):
        raise HTTPException(status_code=400, detail="window must be 1h, 24h or 7d")
    return compute_sla(db, monitor_id, window)
