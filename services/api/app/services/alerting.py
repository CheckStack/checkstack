"""Slack and email delivery for new incidents."""

from __future__ import annotations

import asyncio
import email.message
import logging
import smtplib
import ssl
from email.utils import formatdate
from typing import Any

import httpx
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.config import settings
from app.models.alert_config import AlertConfig
from app.models.incident import Incident
from app.models.monitor import Monitor

log = logging.getLogger("checkstack.alerts")


def _normalize_email_to(cfg: dict[str, Any]) -> list[str]:
    t = cfg.get("to")
    if t is None:
        return []
    if isinstance(t, str):
        return [t] if t.strip() else []
    if isinstance(t, (list, tuple)):
        return [x for x in t if isinstance(x, str) and x.strip()]


def _applicable_configs(
    session: Session,
    monitor: Monitor,
) -> list[AlertConfig]:
    m_id = monitor.id
    return (
        session.query(AlertConfig)
        .filter(AlertConfig.enabled == True)  # noqa: E712
        .filter(
            or_(
                AlertConfig.monitor_id.is_(None),
                AlertConfig.monitor_id == m_id,
            )
        )
        .all()
    )


def _incident_fires_for_monitor(mon: Monitor) -> bool:
    return mon.alerts_enabled


async def _send_slack(
    client: httpx.AsyncClient, webhook: str, text: str, link: str | None = None
) -> bool:
    payload: dict = {"text": text}
    if link:
        payload["attachments"] = [{"text": f"<{link}|Open CheckStack>"}]
    r = await client.post(
        webhook,
        json=payload,
        timeout=20.0,
    )
    if r.is_success:
        return True
    log.warning("slack webhook status %s: %s", r.status_code, r.text[:500])
    return False


def _email_sync(
    to_list: list[str], subject: str, body: str, html: bool = False
) -> None:
    if not to_list or not settings.smtp_host:
        return
    msg = email.message.EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = ", ".join(to_list)
    msg["Date"] = formatdate()
    if html:
        msg.set_content("HTML report not supported in plain client.", subtype="plain")
    else:
        msg.set_content(body, subtype="plain", charset="utf-8")
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as s:
        if settings.smtp_use_tls:
            s.starttls(context=ssl.create_default_context())
        if settings.smtp_user and settings.smtp_password:
            s.login(settings.smtp_user, settings.smtp_password)
        s.send_message(msg, from_addr=settings.smtp_from, to_addrs=to_list)


def build_incident_message(inc: Incident, mon: Monitor) -> str:
    lines = [
        f"*{inc.title}*",
        f"Monitor: {mon.name} — {mon.url}",
        "",
        inc.summary,
        "",
        f"Incident id: {inc.id}  ·  Started: {inc.started_at}",
    ]
    if inc.resolved_at and inc.duration_seconds is not None:
        lines.append(f"Resolved: {inc.resolved_at} (duration: {inc.duration_seconds}s)")
    return "\n".join(lines)


async def send_incident_notifications(session: Session, inc: Incident, mon: Monitor) -> None:
    if not _incident_fires_for_monitor(mon):
        return
    text = build_incident_message(inc, mon)
    public_link = f"{settings.public_base_url.rstrip('/')}/incidents/{inc.id}"
    cfgs = _applicable_configs(session, mon)
    if not cfgs:
        return

    async with httpx.AsyncClient() as client:
        for c in cfgs:
            if c.kind == "slack":
                wh = c.config.get("webhook_url") or settings.slack_default_webhook_url
                if wh:
                    ok = await _send_slack(
                        client,
                        wh,
                        f":rotating_light: New incident (CheckStack)\n\n{text}\n{public_link}",
                    )
                    if not ok:
                        log.warning("failed slack for alert_config id %s", c.id)
            elif c.kind == "email":
                tos = _normalize_email_to(c.config)
                if not tos:
                    log.warning("email alert_config %s: missing config.to", c.id)
                    continue
                subj = f"[CheckStack] {inc.title}"
                body = f"{text}\n\n{public_link}"
                try:
                    await asyncio.to_thread(
                        _email_sync,
                        tos,
                        subj,
                        body,
                    )
                except Exception:  # noqa: BLE001
                    log.exception("email alert failed (config %s)", c.id)


async def try_notify_new_incident(incident_id: int) -> None:
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        inc = db.get(Incident, incident_id)
        if not inc or inc.status != "open":
            return
        mon = db.get(Monitor, inc.monitor_id)
        if not mon:
            return
        await send_incident_notifications(db, inc, mon)
    finally:
        db.close()
