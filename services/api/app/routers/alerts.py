from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.alert_config import AlertConfig

KindT = Literal["slack", "email"]


class AlertConfigCreate(BaseModel):
    kind: KindT
    name: str = "default"
    config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    monitor_id: int | None = None


class AlertConfigRead(BaseModel):
    id: int
    kind: str
    name: str
    config: dict[str, Any]
    enabled: bool
    monitor_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_config(cls, c: AlertConfig) -> "AlertConfigRead":
        return cls(
            id=c.id,
            kind=c.kind,
            name=c.name,
            config=c.config,
            enabled=c.enabled,
            monitor_id=c.monitor_id,
            created_at=c.created_at,
        )


def _validate_config(kind: str, cfg: dict) -> None:
    if kind == "slack" and not cfg.get("webhook_url"):
        raise HTTPException(400, "config.webhook_url is required for slack")
    if kind == "email":
        t = cfg.get("to")
        if not t:
            raise HTTPException(400, "config.to (email or list) is required for email")


router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("", response_model=AlertConfigRead)
def create_alert(payload: AlertConfigCreate, db: Session = Depends(get_db)) -> AlertConfigRead:
    _validate_config(payload.kind, payload.config)
    c = AlertConfig(
        kind=payload.kind,
        name=payload.name,
        config=payload.config,
        enabled=payload.enabled,
        monitor_id=payload.monitor_id,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return AlertConfigRead.from_orm_config(c)


@router.get("", response_model=list[AlertConfigRead])
def list_alerts(db: Session = Depends(get_db)) -> list[AlertConfigRead]:
    q = db.query(AlertConfig).order_by(AlertConfig.id)
    return [AlertConfigRead.from_orm_config(c) for c in q.all()]


@router.delete("/{alert_id}", status_code=204)
def delete_alert(alert_id: int, db: Session = Depends(get_db)) -> Response:
    c = db.get(AlertConfig, alert_id)
    if not c:
        raise HTTPException(404, "not found")
    db.delete(c)
    db.commit()
    return Response(status_code=204)
