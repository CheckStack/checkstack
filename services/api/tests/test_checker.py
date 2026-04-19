import httpx
import pytest

from app.services.checker import check_url


@pytest.mark.asyncio
async def test_check_url_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="ok")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        out = await check_url("https://example.test/health", timeout_seconds=5.0, client=client)
    assert out["ok"] is True
    assert out["status_code"] == 200
    assert out["error_message"] is None


@pytest.mark.asyncio
async def test_check_url_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="no")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        out = await check_url("https://example.test/", timeout_seconds=5.0, client=client)
    assert out["ok"] is False
    assert out["status_code"] == 500
