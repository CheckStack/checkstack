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
        ("consecutive_successes", "ALTER TABLE monitors ADD COLUMN consecutive_successes INTEGER NOT NULL DEFAULT 0"),
        ("last_incident_opened_at", f"ALTER TABLE monitors ADD COLUMN last_incident_opened_at {ts} NULL"),
        ("last_incident_resolved_at", f"ALTER TABLE monitors ADD COLUMN last_incident_resolved_at {ts} NULL"),
        ("slack_webhook_url", "ALTER TABLE monitors ADD COLUMN slack_webhook_url TEXT NULL"),
        ("public_slug", "ALTER TABLE monitors ADD COLUMN public_slug VARCHAR(128) NULL"),
        ("is_public", f"ALTER TABLE monitors ADD COLUMN is_public BOOLEAN NOT NULL {default_bool}"),
    ]:
        if col not in m:
            alters.append(stmt)
    if alters:
        with engine.begin() as conn:
            for stmt in alters:
                conn.execute(text(stmt))
    with engine.begin() as conn:
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_monitors_public_slug ON monitors(public_slug)"))


def ensure_incident_columns(engine: Engine) -> None:
    ic = _cols(engine, "incidents")
    if not ic:
        return
    ts = _TS(engine)
    alters: list[str] = []
    if "duration_seconds" not in ic:
        alters.append("ALTER TABLE incidents ADD COLUMN duration_seconds INTEGER NULL")
    if "slack_down_notified_at" not in ic:
        alters.append(f"ALTER TABLE incidents ADD COLUMN slack_down_notified_at {ts} NULL")
    if "slack_recovered_notified_at" not in ic:
        alters.append(f"ALTER TABLE incidents ADD COLUMN slack_recovered_notified_at {ts} NULL")
    if not alters:
        return
    with engine.begin() as conn:
        for stmt in alters:
            conn.execute(text(stmt))


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


def ensure_uptime_log_table(engine: Engine) -> None:
    insp = inspect(engine)
    is_pg = engine.dialect.name == "postgresql"
    with engine.begin() as conn:
        if not insp.has_table("uptime_log"):
            if is_pg:
                conn.execute(
                    text(
                        """
                    CREATE TABLE IF NOT EXISTS uptime_log (
                        id SERIAL PRIMARY KEY,
                        monitor_id INTEGER NOT NULL REFERENCES monitors(id) ON DELETE CASCADE,
                        status VARCHAR(8) NOT NULL,
                        response_time_ms DOUBLE PRECISION NULL,
                        checked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                        error_message TEXT NULL
                    );
                """
                    )
                )
            else:
                conn.execute(
                    text(
                        """
                    CREATE TABLE IF NOT EXISTS uptime_log (
                        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        monitor_id INTEGER NOT NULL REFERENCES monitors(id) ON DELETE CASCADE,
                        status VARCHAR(8) NOT NULL,
                        response_time_ms FLOAT NULL,
                        checked_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        error_message TEXT NULL
                    );
                """
                    )
                )

        if is_pg:
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_uptime_log_monitor_checked_at ON uptime_log (monitor_id, checked_at);"
                )
            )
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_uptime_log_checked_at ON uptime_log (checked_at);")
            )
        else:
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_uptime_log_monitor_checked_at ON uptime_log (monitor_id, checked_at);"
                )
            )
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_uptime_log_checked_at ON uptime_log (checked_at);")
            )


def run_migrations(engine: Engine) -> None:
    ensure_monitor_tls_and_alerts(engine)
    ensure_incident_columns(engine)
    ensure_tag_tables(engine)
    ensure_alert_config_table(engine)
    ensure_uptime_log_table(engine)
