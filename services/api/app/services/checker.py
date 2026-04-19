import time
from typing import Any

import httpx


async def check_url(
    url: str,
    timeout_seconds: float = 10.0,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    start = time.perf_counter()
    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=timeout_seconds)
    assert client is not None
    try:
        response = await client.get(url, follow_redirects=True)
        latency_ms = (time.perf_counter() - start) * 1000
        ok = 200 <= response.status_code < 400
        return {
            "ok": ok,
            "status_code": response.status_code,
            "latency_ms": round(latency_ms, 2),
            "error_message": None if ok else f"HTTP {response.status_code}",
        }
    except httpx.TimeoutException:
        latency_ms = (time.perf_counter() - start) * 1000
        return {
            "ok": False,
            "status_code": None,
            "latency_ms": round(latency_ms, 2),
            "error_message": "timeout",
        }
    except Exception as exc:  # noqa: BLE001 — surface last-mile errors to monitors
        latency_ms = (time.perf_counter() - start) * 1000
        return {
            "ok": False,
            "status_code": None,
            "latency_ms": round(latency_ms, 2),
            "error_message": str(exc)[:500],
        }
    finally:
        if own_client:
            await client.aclose()
