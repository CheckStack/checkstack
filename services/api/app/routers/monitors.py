from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
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
from app.routers.serializers import to_monitor_read
from app.services.latency_stats import compute_latency_stats
from app.services.metrics import fetch_metrics, parse_metrics_range
from app.services.sla import compute_sla

router = APIRouter(prefix="/monitors", tags=["monitors"])


def _resolve_monitor_tags(
    db: Session,
    *,
    tag_ids: list[int] | None,
    tag_names: list[str] | None,
) -> list[Tag]:
    resolved: dict[int, Tag] = {}

    normalized_names = [t.strip() for t in (tag_names or []) if t and t.strip()]
    for tag_id in tag_ids or []:
        t = db.get(Tag, tag_id)
        if t is None:
            raise HTTPException(status_code=400, detail="one or more tag_ids not found")
        resolved[t.id] = t

    if normalized_names:
        existing = (
            db.query(Tag)
            .filter(func.lower(Tag.name).in_([name.lower() for name in normalized_names]))
            .all()
        )
        existing_by_name = {t.name.lower(): t for t in existing}

        for name in normalized_names:
            key = name.lower()
            if key in existing_by_name:
                resolved[existing_by_name[key].id] = existing_by_name[key]
                continue
            created = Tag(name=name)
            db.add(created)
            db.flush()
            resolved[created.id] = created
            existing_by_name[key] = created

    return list(resolved.values())


@router.post("", response_model=MonitorRead)
def create_monitor(payload: MonitorCreate, db: Session = Depends(get_db)) -> MonitorRead:
    if payload.is_public and not payload.public_slug:
        raise HTTPException(status_code=400, detail="public_slug is required when is_public is true")
    monitor = Monitor(
        name=payload.name,
        url=str(payload.url),
        interval_seconds=payload.interval_seconds,
        timeout_seconds=payload.timeout_seconds,
        failure_threshold=payload.failure_threshold,
        alerts_enabled=payload.alerts_enabled,
        slack_webhook_url=payload.slack_webhook_url,
        public_slug=payload.public_slug,
        is_public=payload.is_public,
    )
    db.add(monitor)
    db.flush()
    tags = _resolve_monitor_tags(db, tag_ids=payload.tag_ids, tag_names=payload.tags)
    if tags:
        monitor.tags = tags
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="public_slug must be unique")
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
    tag: str | None = Query(default=None, description="filter by tag name"),
    db: Session = Depends(get_db),
) -> list[MonitorRead]:
    query = db.query(Monitor).options(joinedload(Monitor.tags))
    if tag_id is not None or tag is not None:
        query = query.join(Monitor.tags)
        if tag_id is not None:
            query = query.filter(Tag.id == tag_id)
        if tag is not None:
            query = query.filter(func.lower(Tag.name) == tag.strip().lower())
        mlist = query.order_by(Monitor.id).distinct().all()
    else:
        mlist = query.order_by(Monitor.id).all()
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
    is_public = d.get("is_public", m.is_public)
    public_slug = d.get("public_slug", m.public_slug)
    if is_public and not public_slug:
        raise HTTPException(status_code=400, detail="public_slug is required when is_public is true")
    tids = d.pop("tag_ids", None)
    tnames = d.pop("tags", None)
    for k, v in d.items():
        setattr(m, k, v)
    if tids is not None or tnames is not None:
        tags = _resolve_monitor_tags(db, tag_ids=tids, tag_names=tnames)
        m.tags = tags
    db.add(m)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="public_slug must be unique")
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
