from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.alert_config import AlertConfig
from app.models.monitor import Monitor
from app.schemas.monitor import MonitorRead, TagRef


def monitor_has_routing_alerts(db: Session, m: Monitor) -> bool:
    n = (
        db.query(AlertConfig)
        .filter(
            AlertConfig.enabled == True,  # noqa: E712
            or_(
                AlertConfig.monitor_id.is_(None),
                AlertConfig.monitor_id == m.id,
            ),
        )
        .count()
    )
    return n > 0


def to_monitor_read(db: Session, m: Monitor) -> MonitorRead:
    tags = [TagRef.model_validate(t) for t in m.tags] if m.tags is not None else []
    return MonitorRead(
        id=m.id,
        name=m.name,
        url=m.url,
        interval_seconds=m.interval_seconds,
        timeout_seconds=m.timeout_seconds,
        failure_threshold=m.failure_threshold,
        consecutive_failures=m.consecutive_failures,
        alerts_enabled=bool(m.alerts_enabled) if m.alerts_enabled is not None else True,
        slack_webhook_url=m.slack_webhook_url,
        public_slug=m.public_slug,
        is_public=bool(m.is_public),
        last_status=m.last_status,
        last_checked_at=m.last_checked_at,
        tls_cert_expires_at=m.tls_cert_expires_at,
        tls_cert_subject=m.tls_cert_subject,
        tls_cert_checked_at=m.tls_cert_checked_at,
        tls_cert_probe_error=m.tls_cert_probe_error,
        tags=tags,
        alerts_will_fire=monitor_has_routing_alerts(db, m) and m.alerts_enabled is not False,
        created_at=m.created_at,
    )


def load_monitors_eager(db: Session) -> list[Monitor]:
    return db.query(Monitor).options(joinedload(Monitor.tags)).order_by(Monitor.id).all()
