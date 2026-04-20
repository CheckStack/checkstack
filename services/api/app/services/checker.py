import time
from typing import Any

import httpx

from app.config import settings


async def check_url(
    url: str,
    timeout_seconds: float | None = None,
    retry_attempts: int | None = None,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    timeout = float(timeout_seconds if timeout_seconds is not None else settings.check_timeout_seconds)
    attempts = max(1, int(retry_attempts if retry_attempts is not None else settings.check_retry_attempts))
    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=timeout)
    assert client is not None
    try:
        last: dict[str, Any] = {
            "ok": False,
            "status_code": None,
            "latency_ms": None,
            "error_message": "unknown error",
            "attempts": attempts,
        }
        for _attempt in range(1, attempts + 1):
            start = time.perf_counter()
            try:
                response = await client.get(url, follow_redirects=True)
                latency_ms = (time.perf_counter() - start) * 1000
                ok = 200 <= response.status_code < 400
                last = {
                    "ok": ok,
                    "status_code": response.status_code,
                    "latency_ms": round(latency_ms, 2),
                    "error_message": None if ok else f"HTTP {response.status_code}",
                    "attempts": _attempt,
                }
                if ok:
                    return last
            except httpx.TimeoutException:
                latency_ms = (time.perf_counter() - start) * 1000
                last = {
                    "ok": False,
                    "status_code": None,
                    "latency_ms": round(latency_ms, 2),
                    "error_message": "timeout",
                    "attempts": _attempt,
                }
            except Exception as exc:  # noqa: BLE001 — surface last-mile errors to monitors
                latency_ms = (time.perf_counter() - start) * 1000
                last = {
                    "ok": False,
                    "status_code": None,
                    "latency_ms": round(latency_ms, 2),
                    "error_message": str(exc)[:500],
                    "attempts": _attempt,
                }
        return last
    finally:
        if own_client:
            await client.aclose()
