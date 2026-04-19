from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.monitor import Monitor
from app.services.sla import compute_sla

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/status", response_model=dict)
def public_status(db: Session = Depends(get_db)) -> dict:
    out: list[dict] = []
    for m in db.query(Monitor).order_by(Monitor.id).all():
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
