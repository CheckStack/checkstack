import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models.check_result import CheckResult
from app.models.monitor import Monitor
from app.services.checker import check_url
from app.services.incidents import maybe_create_incident, resolve_open_incidents

log = logging.getLogger("checkstack.worker")


def _should_run_check(monitor: Monitor, now: datetime) -> bool:
    if monitor.last_checked_at is None:
        return True
    elapsed = (now - monitor.last_checked_at).total_seconds()
    return elapsed >= monitor.interval_seconds


async def run_check_for_monitor(db: Session, monitor: Monitor, now: datetime) -> None:
    result = await check_url(monitor.url, timeout_seconds=float(monitor.timeout_seconds))
    check = CheckResult(
        monitor_id=monitor.id,
        ok=result["ok"],
        status_code=result["status_code"],
        latency_ms=result["latency_ms"],
        error_message=result["error_message"],
        checked_at=now,
    )
    db.add(check)

    monitor.last_checked_at = now
    monitor.last_status = "up" if result["ok"] else "down"

    if result["ok"]:
        monitor.consecutive_failures = 0
        resolved = resolve_open_incidents(db, monitor.id)
        if resolved:
            log.info("resolved %s open incident(s) for monitor %s", resolved, monitor.id)
    else:
        monitor.consecutive_failures += 1
        incident = maybe_create_incident(
            db,
            monitor,
            status_code=result["status_code"],
            error_message=result["error_message"],
        )
        if incident:
            log.warning("opened incident %s for monitor %s", incident.id, monitor.id)

    db.commit()


async def run_once() -> None:
    now = datetime.now(UTC)
    db = SessionLocal()
    try:
        monitors = db.query(Monitor).order_by(Monitor.id.asc()).all()
        for monitor in monitors:
            if not _should_run_check(monitor, now):
                continue
            await run_check_for_monitor(db, monitor, now)
    finally:
        db.close()


async def schedule_checks() -> None:
    logging.basicConfig(level=logging.INFO)
    Base.metadata.create_all(bind=engine)
    log.info("uptime worker started (interval %ss)", settings.check_interval_seconds)
    while True:
        try:
            await run_once()
        except Exception:  # noqa: BLE001
            log.exception("check cycle failed")
        await asyncio.sleep(settings.check_interval_seconds)


def main() -> None:
    asyncio.run(schedule_checks())


if __name__ == "__main__":
    main()
