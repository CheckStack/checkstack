"""Lightweight additive migrations for single-node / Compose installs."""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def ensure_monitor_tls_columns(engine: Engine) -> None:
    inspector = inspect(engine)
    if not inspector.has_table("monitors"):
        return
    existing = {c["name"] for c in inspector.get_columns("monitors")}
    dialect = engine.dialect.name
    is_pg = dialect == "postgresql"
    ts_type = "TIMESTAMPTZ" if is_pg else "TIMESTAMP"

    alters: list[str] = []
    if "tls_cert_expires_at" not in existing:
        alters.append(f"ALTER TABLE monitors ADD COLUMN tls_cert_expires_at {ts_type} NULL")
    if "tls_cert_subject" not in existing:
        alters.append("ALTER TABLE monitors ADD COLUMN tls_cert_subject TEXT NULL")
    if "tls_cert_checked_at" not in existing:
        alters.append(f"ALTER TABLE monitors ADD COLUMN tls_cert_checked_at {ts_type} NULL")
    if "tls_cert_probe_error" not in existing:
        alters.append("ALTER TABLE monitors ADD COLUMN tls_cert_probe_error TEXT NULL")

    if not alters:
        return
    with engine.begin() as conn:
        for stmt in alters:
            conn.execute(text(stmt))
