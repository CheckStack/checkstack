from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.database import Base, SessionLocal, engine
from app.models.incident import Incident
from app.models.monitor import Monitor
from app.models.uptime_log import UptimeLog
from app.services.incidents import maybe_create_incident, resolve_open_incidents
from app.services.sla import compute_sla
from app.services.tls import TlsCertInfo
from app.workers import uptime_worker


def _reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_incident_creation_and_resolution_logic(monkeypatch) -> None:
    _reset_db()
    monkeypatch.setattr(uptime_worker.settings, "incident_open_after_failures", 1)
    monkeypatch.setattr(uptime_worker.settings, "incident_close_after_successes", 1)
    monkeypatch.setattr(uptime_worker.settings, "incident_debounce_seconds", 0)

    with SessionLocal() as db:
        monitor = Monitor(
            name="Orders API",
            url="https://orders.example.test/health",
            interval_seconds=60,
            timeout_seconds=5,
            failure_threshold=1,
        )
        db.add(monitor)
        db.commit()
        db.refresh(monitor)

        monitor.consecutive_failures = 1
        incident = maybe_create_incident(db, monitor, status_code=500, error_message="HTTP 500")
        assert incident is not None
        assert incident.status == "open"
        incident.started_at = datetime.now(timezone.utc) - timedelta(seconds=30)
        db.flush()

        monitor.consecutive_successes = 1
        resolved = resolve_open_incidents(db, monitor)
        assert len(resolved) == 1
        assert resolved[0].status == "resolved"
        assert resolved[0].duration_seconds is not None


def test_sla_calculation_uses_sqlite_uptime_logs() -> None:
    _reset_db()
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        monitor = Monitor(
            name="Billing API",
            url="https://billing.example.test/health",
            interval_seconds=60,
            timeout_seconds=5,
            failure_threshold=1,
        )
        db.add(monitor)
        db.commit()
        db.refresh(monitor)

        db.add_all(
            [
                UptimeLog(
                    monitor_id=monitor.id,
                    status="UP",
                    response_time_ms=100,
                    checked_at=now - timedelta(minutes=20),
                ),
                UptimeLog(
                    monitor_id=monitor.id,
                    status="DOWN",
                    response_time_ms=1000,
                    checked_at=now - timedelta(minutes=10),
                    error_message="timeout",
                ),
                UptimeLog(
                    monitor_id=monitor.id,
                    status="UP",
                    response_time_ms=120,
                    checked_at=now - timedelta(minutes=1),
                ),
            ]
        )
        db.commit()

        sla = compute_sla(db, monitor.id, "24h")
        assert sla["total_checks"] == 3
        assert sla["successful_checks"] == 2
        assert sla["uptime_percent"] == 66.667


@pytest.mark.asyncio
async def test_uptime_worker_run_once_creates_incident_without_real_http(monkeypatch) -> None:
    _reset_db()
    monkeypatch.setattr(uptime_worker.settings, "incident_open_after_failures", 1)
    monkeypatch.setattr(uptime_worker.settings, "incident_debounce_seconds", 0)
    monkeypatch.setattr(uptime_worker.settings, "check_retry_attempts", 1)

    async def fake_check_url(url: str, timeout_seconds: float, retry_attempts: int) -> dict:
        return {
            "ok": False,
            "status_code": 500,
            "latency_ms": 35.0,
            "error_message": "HTTP 500",
            "attempts": 1,
        }

    async def fake_tls_probe(url: str, timeout_seconds: float) -> TlsCertInfo:
        return TlsCertInfo(None, None, "tls disabled in test")

    async def noop_alert(*args, **kwargs) -> None:
        return None

    monkeypatch.setattr(uptime_worker, "check_url", fake_check_url)
    monkeypatch.setattr(uptime_worker, "probe_tls_certificate", fake_tls_probe)
    monkeypatch.setattr(uptime_worker, "send_incident_opened_alert", noop_alert)
    monkeypatch.setattr(uptime_worker, "send_incident_resolved_alert", noop_alert)

    with SessionLocal() as db:
        db.add(
            Monitor(
                name="Worker Monitor",
                url="https://worker.example.test/health",
                interval_seconds=1,
                timeout_seconds=5,
                failure_threshold=1,
            )
        )
        db.commit()

    await uptime_worker.run_once()

    with SessionLocal() as db:
        monitor = db.query(Monitor).filter(Monitor.name == "Worker Monitor").one()
        incidents = db.query(Incident).filter(Incident.monitor_id == monitor.id).all()
        uptime_logs = db.query(UptimeLog).filter(UptimeLog.monitor_id == monitor.id).all()
        assert monitor.last_status == "down"
        assert monitor.consecutive_failures == 1
        assert len(incidents) == 1
        assert incidents[0].status == "open"
        assert len(uptime_logs) == 1
