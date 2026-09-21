from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ServiceHeartbeat(Base):
    """Heartbeat фоновых сервисов (worker) — питает публичную status page."""

    __tablename__ = "service_heartbeats"

    name: Mapped[str] = mapped_column(String(50), primary_key=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
