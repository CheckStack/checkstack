import os
import socket

import pytest

# Keep tests docker-free and deterministic.
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")


@pytest.fixture(autouse=True)
def block_external_network(monkeypatch: pytest.MonkeyPatch) -> None:
    original_connect = socket.socket.connect

    def guarded_connect(sock: socket.socket, address):  # type: ignore[no-untyped-def]
        host = address[0] if isinstance(address, tuple) and address else None
        if host in {"127.0.0.1", "localhost"}:
            return original_connect(sock, address)
        raise RuntimeError(f"external network disabled in tests: {address!r}")

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)

