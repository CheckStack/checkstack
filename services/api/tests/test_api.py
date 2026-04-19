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
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Example"
    mid = body["id"]

    listed = client.get("/monitors").json()
    assert len(listed) == 1

    sla = client.get(f"/monitors/{mid}/sla", params={"window": "24h"}).json()
    assert sla["total_checks"] == 0
    assert sla["uptime_percent"] == 100.0

    assert client.delete(f"/monitors/{mid}").status_code == 204
