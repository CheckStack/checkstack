import os
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.incident import Incident  # noqa: E402
from app.models.uptime_log import UptimeLog  # noqa: E402


@pytest.fixture()
def client() -> TestClient:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c


def test_healthz(client: TestClient) -> None:
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_monitor_crud(client: TestClient) -> None:
    r = client.post(
        "/monitors",
        json={
            "name": "Example",
            "url": "https://example.com",
            "interval_seconds": 60,
            "timeout_seconds": 10,
            "failure_threshold": 3,
            "slack_webhook_url": "https://hooks.slack.test/example",
            "is_public": True,
            "public_slug": "example-status",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Example"
    assert body["slack_webhook_url"] == "https://hooks.slack.test/example"
    assert body["is_public"] is True
    assert body["public_slug"] == "example-status"
    mid = body["id"]

    listed = client.get("/monitors").json()
    assert len(listed) == 1

    metrics = client.get(f"/monitors/{mid}/metrics", params={"range": "24h"})
    assert metrics.status_code == 200
    assert metrics.json() == []

    sla = client.get(f"/monitors/{mid}/sla", params={"window": "1h"}).json()
    assert sla["total_checks"] == 0
    assert sla["uptime_percent"] == 100.0

    assert client.delete(f"/monitors/{mid}").status_code == 204


def test_tags_uptime_alerts_and_incident(client: TestClient) -> None:
    r = client.post("/tags", json={"name": "api", "color": "#0ea5e9"})
    assert r.status_code == 200
    tag = r.json()
    tag_id = tag["id"]

    m = client.post(
        "/monitors",
        json={
            "name": "S",
            "url": "https://example.com",
            "interval_seconds": 60,
            "timeout_seconds": 5,
            "failure_threshold": 1,
            "alerts_enabled": True,
            "tag_ids": [tag_id],
        },
    )
    assert m.status_code == 200
    mid = m.json()["id"]
    list_m = client.get(f"/monitors?tag_id={tag_id}").json()
    assert any(x["id"] == mid for x in list_m)

    up = client.get(f"/uptime/{mid}", params={"range": "1h"}).json()
    assert up["monitor_id"] == mid
    assert "points" in up

    st = client.get(f"/monitors/{mid}/stats", params={"window": "24h"}).json()
    assert st["monitor_id"] == mid
    assert "sla" in st

    ar = client.post(
        "/alerts",
        json={"kind": "email", "name": "a", "config": {"to": "x@y.com"}, "enabled": True, "monitor_id": None},
    )
    assert ar.status_code == 200
    aid = ar.json()["id"]
    d = client.delete(f"/alerts/{aid}")
    assert d.status_code == 204
    assert d.text == ""


def test_get_incident_not_found(client: TestClient) -> None:
    d = client.get("/incidents/9999")
    assert d.status_code == 404


def test_public_status_endpoint_only_exposes_public_monitors(client: TestClient) -> None:
    public_m = client.post(
        "/monitors",
        json={
            "name": "Public API",
            "url": "https://example.com/public",
            "interval_seconds": 60,
            "timeout_seconds": 10,
            "failure_threshold": 3,
            "is_public": True,
            "public_slug": "public-api",
        },
    )
    assert public_m.status_code == 200

    private_m = client.post(
        "/monitors",
        json={
            "name": "Private API",
            "url": "https://example.com/private",
            "interval_seconds": 60,
            "timeout_seconds": 10,
            "failure_threshold": 3,
            "is_public": False,
        },
    )
    assert private_m.status_code == 200

    listing = client.get("/public/status")
    assert listing.status_code == 200
    monitor_names = [m["name"] for m in listing.json()["monitors"]]
    assert "Public API" in monitor_names
    assert "Private API" not in monitor_names

    by_slug = client.get("/status/public-api")
    assert by_slug.status_code == 200
    payload = by_slug.json()
    assert payload["monitor"]["name"] == "Public API"
    assert payload["powered_by"] == "CheckStack"

    not_found = client.get("/status/private-api")
    assert not_found.status_code == 404


def test_incident_detail_includes_logs_and_failure_reason(client: TestClient) -> None:
    m = client.post(
        "/monitors",
        json={
            "name": "API monitor",
            "url": "https://example.com/health",
            "interval_seconds": 60,
            "timeout_seconds": 5,
            "failure_threshold": 3,
        },
    )
    assert m.status_code == 200
    monitor_id = m.json()["id"]

    started = datetime.now(timezone.utc) - timedelta(minutes=10)
    resolved = started + timedelta(minutes=5)

    with SessionLocal() as db:
        inc = Incident(
            monitor_id=monitor_id,
            title="Incident: API monitor unavailable",
            summary="auto incident",
            status="resolved",
            detected_by="test",
            started_at=started,
            resolved_at=resolved,
            duration_seconds=300,
        )
        db.add(inc)
        db.flush()
        incident_id = inc.id

        db.add_all(
            [
                UptimeLog(
                    monitor_id=monitor_id,
                    status="DOWN",
                    response_time_ms=1200.0,
                    checked_at=started + timedelta(minutes=1),
                    error_message="HTTP 500",
                ),
                UptimeLog(
                    monitor_id=monitor_id,
                    status="DOWN",
                    response_time_ms=1300.0,
                    checked_at=started + timedelta(minutes=2),
                    error_message="HTTP 500",
                ),
                UptimeLog(
                    monitor_id=monitor_id,
                    status="DOWN",
                    response_time_ms=900.0,
                    checked_at=started + timedelta(minutes=3),
                    error_message="timeout",
                ),
                UptimeLog(
                    monitor_id=monitor_id,
                    status="UP",
                    response_time_ms=220.0,
                    checked_at=started + timedelta(minutes=4),
                    error_message=None,
                ),
            ]
        )
        db.commit()

    detail = client.get(f"/incidents/{incident_id}")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["monitor"]["id"] == monitor_id
    assert payload["failure_reason_summary"] == "HTTP 500"
    assert payload["duration_seconds"] == 300
    assert len(payload["uptime_logs"]) == 4
