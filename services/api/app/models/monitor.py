from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.tag import Tag, monitor_tags


class Monitor(Base):
    __tablename__ = "monitors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    failure_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    consecutive_successes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    alerts_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    slack_webhook_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_incident_opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_incident_resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tls_cert_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tls_cert_subject: Mapped[str | None] = mapped_column(Text, nullable=True)
    tls_cert_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tls_cert_probe_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    check_results = relationship("CheckResult", back_populates="monitor", cascade="all, delete-orphan")
    incidents = relationship("Incident", back_populates="monitor", cascade="all, delete-orphan")
    tags: Mapped[list[Tag]] = relationship(
        Tag,
        secondary=monitor_tags,
        back_populates="monitors",
    )
    alert_configs = relationship(
        "AlertConfig",
        back_populates="monitor",
        cascade="all, delete-orphan",
    )
