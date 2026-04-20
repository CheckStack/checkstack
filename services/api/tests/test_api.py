import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


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
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Example"
    assert body["slack_webhook_url"] == "https://hooks.slack.test/example"
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
