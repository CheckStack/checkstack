from __future__ import annotations

import logging
from datetime import UTC, datetime

import httpx
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.config import settings
from app.models.alert_config import AlertConfig
from app.models.incident import Incident
from app.models.monitor import Monitor

log = logging.getLogger("checkstack.alert_service")


def _effective_webhook_url(monitor: Monitor) -> str:
    return (monitor.slack_webhook_url or settings.slack_webhook_url or settings.slack_default_webhook_url).strip()


def _slack_webhook_urls(db: Session, monitor: Monitor) -> list[str]:
    urls: list[str] = []
    default_url = _effective_webhook_url(monitor)
    if default_url:
        urls.append(default_url)

    cfgs = (
        db.query(AlertConfig)
        .filter(AlertConfig.kind == "slack")
        .filter(AlertConfig.enabled == True)  # noqa: E712
        .filter(or_(AlertConfig.monitor_id.is_(None), AlertConfig.monitor_id == monitor.id))
        .order_by(AlertConfig.id.asc())
        .all()
    )
    for cfg in cfgs:
        webhook_url = str(cfg.config.get("webhook_url") or "").strip()
        if webhook_url:
            urls.append(webhook_url)

    # Deduplicate while preserving order.
    unique_urls = list(dict.fromkeys(urls))
    return unique_urls


def _fmt_ts(ts: datetime | None) -> str:
    if ts is None:
        return "unknown"
    return ts.astimezone(UTC).isoformat()


def _opened_message(incident: Incident, monitor: Monitor) -> str:
    return "\n".join(
        [
            ":red_circle: *CheckStack Incident OPENED*",
            f"Monitor: {monitor.name}",
            f"URL: {monitor.url}",
            "Status: DOWN",
            f"Timestamp: {_fmt_ts(incident.started_at)}",
            f"Incident ID: {incident.id}",
        ]
    )


def _resolved_message(incident: Incident, monitor: Monitor) -> str:
    duration = f"{incident.duration_seconds}s" if incident.duration_seconds is not None else "unknown"
    return "\n".join(
        [
            ":large_green_circle: *CheckStack Incident RESOLVED*",
            f"Monitor: {monitor.name}",
            f"URL: {monitor.url}",
            "Status: RECOVERED",
            f"Timestamp: {_fmt_ts(incident.resolved_at)}",
            f"Incident Duration: {duration}",
            f"Incident ID: {incident.id}",
        ]
    )


async def _post_slack(webhook_url: str, message: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(webhook_url, json={"text": message})
        if response.is_success:
            return True
        log.warning("slack webhook returned status=%s body=%s", response.status_code, response.text[:500])
        return False
    except Exception:  # noqa: BLE001
        log.exception("failed posting Slack webhook")
        return False


async def send_incident_opened_alert(db: Session, incident: Incident, monitor: Monitor) -> None:
    if monitor.alerts_enabled is False:
        return
    if incident.slack_down_notified_at is not None:
        return
    webhook_urls = _slack_webhook_urls(db, monitor)
    if not webhook_urls:
        return

    ok_any = False
    for webhook_url in webhook_urls:
        ok = await _post_slack(webhook_url, _opened_message(incident, monitor))
        ok_any = ok_any or ok
    if not ok_any:
        return

    incident.slack_down_notified_at = datetime.now(UTC)
    db.add(incident)
    db.commit()


async def send_incident_resolved_alert(db: Session, incident: Incident, monitor: Monitor) -> None:
    if monitor.alerts_enabled is False:
        return
    if incident.slack_recovered_notified_at is not None:
        return
    webhook_urls = _slack_webhook_urls(db, monitor)
    if not webhook_urls:
        return

    ok_any = False
    for webhook_url in webhook_urls:
        ok = await _post_slack(webhook_url, _resolved_message(incident, monitor))
        ok_any = ok_any or ok
    if not ok_any:
        return

    incident.slack_recovered_notified_at = datetime.now(UTC)
    db.add(incident)
    db.commit()
