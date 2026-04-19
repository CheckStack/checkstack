"""TLS certificate inspection for HTTPS monitors (expiry + subject)."""

from __future__ import annotations

import asyncio
import email.utils
import logging
import ssl
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

log = logging.getLogger("checkstack.tls")


def _format_subject(subject: Any) -> str | None:
    if not subject:
        return None
    parts: list[str] = []
    for rdn in subject:
        for attr, val in rdn:
            parts.append(f"{attr}={val}")
    return ", ".join(parts) if parts else None


def _subject_from_peercert(cert: dict[str, Any]) -> str | None:
    return _format_subject(cert.get("subject"))


def _parse_not_after(cert: dict[str, Any]) -> datetime | None:
    raw = cert.get("notAfter")
    if not raw or not isinstance(raw, str):
        return None
    dt = email.utils.parsedate_to_datetime(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


@dataclass
class TlsCertInfo:
    expires_at: datetime | None
    subject: str | None
    error: str | None


async def probe_tls_certificate(url: str, timeout_seconds: float) -> TlsCertInfo:
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https":
        return TlsCertInfo(None, None, None)

    host = parsed.hostname
    if not host:
        return TlsCertInfo(None, None, "missing host in URL")

    port = parsed.port or 443

    # Read leaf certificate for expiry even if chain validation would fail (monitoring use case).
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2

    writer: asyncio.StreamWriter | None = None
    try:
        _reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port, ssl=ctx, server_hostname=host),
            timeout=timeout_seconds,
        )
        ssl_obj = writer.get_extra_info("ssl_object")
        if ssl_obj is None:
            return TlsCertInfo(None, None, "TLS handshake did not produce a session")
        cert = ssl_obj.getpeercert()
        if not cert:
            return TlsCertInfo(None, None, "no peer certificate returned")
        expires = _parse_not_after(cert)
        subject = _subject_from_peercert(cert)
        return TlsCertInfo(expires, subject, None)
    except TimeoutError:
        return TlsCertInfo(None, None, "tls probe timeout")
    except Exception as exc:  # noqa: BLE001
        log.debug("tls probe failed for %s: %s", url, exc)
        return TlsCertInfo(None, None, str(exc)[:500])
    finally:
        if writer is not None:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:  # noqa: BLE001
                pass
