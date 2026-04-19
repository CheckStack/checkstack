"""Lightweight additive schema updates for single-node / Compose installs."""

from collections.abc import Callable

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

_TS: Callable[[Engine], str] = lambda e: "TIMESTAMPTZ" if e.dialect.name == "postgresql" else "TIMESTAMP"


def _cols(engine: Engine, table: str) -> set[str]:
    insp = inspect(engine)
    if not insp.has_table(table):
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def ensure_monitor_tls_and_alerts(engine: Engine) -> None:
    m = _cols(engine, "monitors")
    if not m or "id" not in m:
        return
    alters: list[str] = []
    ts = _TS(engine)
    default_bool = "DEFAULT true" if engine.dialect.name == "postgresql" else "DEFAULT 1"
    for col, stmt in [
        ("tls_cert_expires_at", f"ALTER TABLE monitors ADD COLUMN tls_cert_expires_at {ts} NULL"),
        ("tls_cert_subject", "ALTER TABLE monitors ADD COLUMN tls_cert_subject TEXT NULL"),
        ("tls_cert_checked_at", f"ALTER TABLE monitors ADD COLUMN tls_cert_checked_at {ts} NULL"),
        ("tls_cert_probe_error", "ALTER TABLE monitors ADD COLUMN tls_cert_probe_error TEXT NULL"),
        ("alerts_enabled", f"ALTER TABLE monitors ADD COLUMN alerts_enabled BOOLEAN NOT NULL {default_bool}"),
    ]:
        if col not in m:
            alters.append(stmt)
    if alters:
        with engine.begin() as conn:
            for stmt in alters:
                conn.execute(text(stmt))


def ensure_incident_columns(engine: Engine) -> None:
    ic = _cols(engine, "incidents")
    if not ic or "duration_seconds" in ic:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE incidents ADD COLUMN duration_seconds INTEGER NULL"))


def ensure_tag_tables(engine: Engine) -> None:
    insp = inspect(engine)
    if insp.has_table("tags") and insp.has_table("monitor_tags"):
        return
    is_pg = engine.dialect.name == "postgresql"
    with engine.begin() as conn:
        if is_pg:
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS tags (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(64) NOT NULL,
                    color VARCHAR(32) NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    CONSTRAINT uq_tags_name UNIQUE (name)
                );
            """
                )
            )
        else:
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(64) NOT NULL,
                    color VARCHAR(32) NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT uq_tags_name UNIQUE (name)
                );
            """
                )
            )
        if is_pg:
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS monitor_tags (
                    monitor_id INTEGER NOT NULL REFERENCES monitors(id) ON DELETE CASCADE,
                    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
                    PRIMARY KEY (monitor_id, tag_id)
                );
            """
                )
            )
        else:
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS monitor_tags (
                    monitor_id INTEGER NOT NULL REFERENCES monitors(id) ON DELETE CASCADE,
                    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
                    PRIMARY KEY (monitor_id, tag_id)
                );
            """
                )
            )


def ensure_alert_config_table(engine: Engine) -> None:
    insp = inspect(engine)
    if insp.has_table("alert_configs"):
        return
    is_pg = engine.dialect.name == "postgresql"
    with engine.begin() as conn:
        if is_pg:
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS alert_configs (
                    id SERIAL PRIMARY KEY,
                    kind VARCHAR(32) NOT NULL,
                    name VARCHAR(128) NOT NULL DEFAULT 'default',
                    config JSONB NOT NULL DEFAULT '{}'::jsonb,
                    enabled BOOLEAN NOT NULL DEFAULT true,
                    monitor_id INTEGER NULL REFERENCES monitors(id) ON DELETE CASCADE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );
            """
                )
            )
        else:
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS alert_configs (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    kind VARCHAR(32) NOT NULL,
                    name VARCHAR(128) NOT NULL DEFAULT 'default',
                    config JSON NOT NULL DEFAULT ('{}'),
                    enabled BOOLEAN NOT NULL DEFAULT 1,
                    monitor_id INTEGER NULL REFERENCES monitors(id) ON DELETE CASCADE,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """
                )
            )


def run_migrations(engine: Engine) -> None:
    ensure_monitor_tls_and_alerts(engine)
    ensure_incident_columns(engine)
    ensure_tag_tables(engine)
    ensure_alert_config_table(engine)
