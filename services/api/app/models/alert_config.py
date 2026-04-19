from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _config_default() -> dict[str, Any]:
    return {}


class AlertConfig(Base):
    """An outbound channel. If monitor_id is null, the alert applies to every monitor (subject to that monitor’s alerts_enabled)."""

    __tablename__ = "alert_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # slack | email
    name: Mapped[str] = mapped_column(String(128), nullable=False, default="default")
    config: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=_config_default,
        insert_default=_config_default,
        nullable=False,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    monitor_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("monitors.id", ondelete="CASCADE"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    monitor: Mapped[object | None] = relationship(  # Monitor
        "Monitor",
        back_populates="alert_configs",
        foreign_keys=[monitor_id],
    )
