from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.monitor import Monitor
from app.services.uptime_series import get_uptime_series

router = APIRouter(prefix="/uptime", tags=["uptime"])


@router.get("/{monitor_id}", response_model=dict)
def get_uptime(
    monitor_id: int,
    time_range: str = Query(
        "24h",
        description="1h, 24h, 7d, or 30d",
        alias="range",
    ),
    db: Session = Depends(get_db),
) -> dict:
    m = db.get(Monitor, monitor_id)
    if not m:
        raise HTTPException(404, "monitor not found")
    r = (time_range or "24h").lower()
    if r not in ("1h", "24h", "7d", "30d"):
        raise HTTPException(400, "range must be one of: 1h, 24h, 7d, 30d")
    return get_uptime_series(db, monitor_id, r)
