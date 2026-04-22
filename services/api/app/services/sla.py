from sqlalchemy.orm import Session

from app.services.metrics import compute_sla_from_uptime_log


def compute_sla(db: Session, monitor_id: int, window: str) -> dict:
    return compute_sla_from_uptime_log(db, monitor_id, window)
