from __future__ import annotations

import asyncio
import email.message
import logging
import smtplib
import ssl
from datetime import datetime, timezone
from email.utils import formatdate
from typing import Any

import httpx
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.config import settings
from app.models.alerting import AlertChannel, AlertRule
from app.models.monitor import Monitor

log = logging.getLogger("checkstack.alerting")


class AlertDispatcher:
    """Extensible dispatcher for outbound alert integrations."""

    async def send(self, channel: AlertChannel, payload: dict[str, Any]) -> None:
        channel_type = channel.type.lower()
        if channel_type == "slack":
            await self._send_slack(channel.config, payload)
        elif channel_type == "email":
            await self._send_email(channel.config, payload)
        elif channel_type == "webhook":
            await self._send_webhook(channel.config, payload)
        else:
            log.warning("unknown alert channel type=%s channel_id=%s", channel.type, channel.id)

    async def _send_slack(self, config: dict[str, Any], payload: dict[str, Any]) -> None:
        webhook = str(config.get("webhook_url") or "").strip()
        if not webhook:
            log.warning("slack channel missing webhook_url")
            return
        body = {
            "text": f"[{payload['trigger_type']}] {payload['monitor_name']} ({payload['monitor_url']}) at {payload['timestamp']}"
        }
        await self._post_json(webhook, body)

    async def _send_webhook(self, config: dict[str, Any], payload: dict[str, Any]) -> None:
        webhook = str(config.get("url") or config.get("webhook_url") or "").strip()
        if not webhook:
            log.warning("webhook channel missing url")
            return
        await self._post_json(webhook, payload)

    async def _send_email(self, config: dict[str, Any], payload: dict[str, Any]) -> None:
        to = config.get("to")
        to_list = [to] if isinstance(to, str) else [x for x in (to or []) if isinstance(x, str)]
        if not to_list or not settings.smtp_host:
            log.warning("email channel missing recipients or smtp_host")
            return

        subject = f"[CheckStack] {payload['trigger_type']}: {payload['monitor_name']}"
        body = f"Monitor: {payload['monitor_name']}\nURL: {payload['monitor_url']}\nStatus: {payload['trigger_type']}\nAt: {payload['timestamp']}"
        await asyncio.to_thread(self._send_email_sync, to_list, subject, body)

    def _send_email_sync(self, to_list: list[str], subject: str, body: str) -> None:
        msg = email.message.EmailMessage()
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from
        msg["To"] = ", ".join(to_list)
        msg["Date"] = formatdate()
        msg.set_content(body, subtype="plain", charset="utf-8")

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls(context=ssl.create_default_context())
            if settings.smtp_user and settings.smtp_password:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg, from_addr=settings.smtp_from, to_addrs=to_list)

    async def _post_json(self, url: str, payload: dict[str, Any]) -> None:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(url, json=payload)
            if not response.is_success:
                log.warning("alert post failed status=%s body=%s", response.status_code, response.text[:500])


async def enqueue_status_change_alerts(db: Session, monitor: Monitor, trigger_type: str, happened_at: datetime) -> None:
    rules = (
        db.query(AlertRule)
        .join(AlertChannel, AlertRule.channel_id == AlertChannel.id)
        .filter(AlertRule.is_active == True)  # noqa: E712
        .filter(AlertChannel.is_active == True)  # noqa: E712
        .filter(AlertRule.trigger_type == trigger_type)
        .filter(or_(AlertRule.monitor_id.is_(None), AlertRule.monitor_id == monitor.id))
        .all()
    )
    if not rules:
        return

    payload = {
        "monitor_id": monitor.id,
        "monitor_name": monitor.name,
        "monitor_url": monitor.url,
        "trigger_type": trigger_type,
        "timestamp": happened_at.astimezone(timezone.utc).isoformat(),
    }
    dispatcher = AlertDispatcher()
    for rule in rules:
        asyncio.create_task(dispatcher.send(rule.channel, payload))
