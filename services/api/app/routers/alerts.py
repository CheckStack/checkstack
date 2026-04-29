from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.auth import get_current_user
from app.models.alerting import AlertChannel, AlertRule
from app.models.monitor import Monitor
from app.services.alerting import AlertDispatcher

router = APIRouter(tags=["alerts"])

ChannelType = Literal["slack", "email", "webhook"]
TriggerType = Literal["DOWN", "RECOVERY"]


class AlertChannelCreate(BaseModel):
    type: ChannelType
    config: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class AlertChannelRead(AlertChannelCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertRuleCreate(BaseModel):
    monitor_id: int | None = None
    channel_id: int
    trigger_type: TriggerType
    is_active: bool = True


class AlertRuleRead(AlertRuleCreate):
    id: int

    model_config = {"from_attributes": True}


@router.post("/alert-channels", response_model=AlertChannelRead)
def create_alert_channel(payload: AlertChannelCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> AlertChannel:
    c = AlertChannel(type=payload.type, config=payload.config, is_active=payload.is_active, user_id=current_user.id, org_id=current_user.org_id)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@router.get("/alert-channels", response_model=list[AlertChannelRead])
def list_alert_channels(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[AlertChannel]:
    return db.query(AlertChannel).filter(AlertChannel.user_id == current_user.id).order_by(AlertChannel.id.asc()).all()


@router.post("/alert-rules", response_model=AlertRuleRead)
def create_alert_rule(payload: AlertRuleCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> AlertRule:
    ch = db.query(AlertChannel).filter(AlertChannel.id == payload.channel_id, AlertChannel.user_id == current_user.id).one_or_none()
    if ch is None:
        raise HTTPException(404, "channel not found")
    if payload.monitor_id is not None and db.get(Monitor, payload.monitor_id) is None:
        raise HTTPException(404, "monitor not found")
    rule = AlertRule(**payload.model_dump(), user_id=current_user.id, org_id=current_user.org_id)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.post("/alert-channels/{channel_id}/test")
async def test_alert_channel(channel_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict[str, str]:
    channel = db.query(AlertChannel).filter(AlertChannel.id == channel_id, AlertChannel.user_id == current_user.id).one_or_none()
    if not channel:
        raise HTTPException(404, "channel not found")
    payload = {
        "monitor_id": 0,
        "monitor_name": "Sample Monitor",
        "monitor_url": "https://example.com/health",
        "trigger_type": "DOWN",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await AlertDispatcher().send(channel, payload)
    return {"status": "sent"}
