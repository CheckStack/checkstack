import pytest

from app.services.tls import TlsCertInfo, _parse_not_after, _subject_from_peercert, probe_tls_certificate


def test_subject_from_peercert_github_style() -> None:
    cert = {"subject": ((("commonName", "github.com"),),)}
    subj = _subject_from_peercert(cert)
    assert subj is not None
    assert "github.com" in subj


def test_parse_not_after() -> None:
    cert = {"notAfter": "Feb  1 23:59:59 2027 GMT"}
    dt = _parse_not_after(cert)
    assert dt is not None
    assert dt.tzinfo is not None
    assert dt.year == 2027 and dt.month == 2


@pytest.mark.asyncio
async def test_probe_skips_http() -> None:
    out = await probe_tls_certificate("http://example.com/", timeout_seconds=2.0)
    assert out == TlsCertInfo(None, None, None)


@pytest.mark.asyncio
async def test_probe_invalid_scheme_host() -> None:
    out = await probe_tls_certificate("https:///nohost", timeout_seconds=2.0)
    assert out.error is not None
