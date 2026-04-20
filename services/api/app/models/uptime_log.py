from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UptimeLog(Base):
    __tablename__ = "uptime_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    monitor_id: Mapped[int] = mapped_column(ForeignKey("monitors.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(8), nullable=False)
    response_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    monitor = relationship("Monitor")
