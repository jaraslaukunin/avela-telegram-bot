import uuid
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Network(Base):
    """Медицинская сеть — верхний уровень multi-tenant иерархии."""

    __tablename__ = "networks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    branches: Mapped[list["Branch"]] = relationship(
        back_populates="network", lazy="selectin"
    )


class Branch(Base):
    """Филиал сети. Хранит IANA timezone — все бизнес-правила времени считаются по нему."""

    __tablename__ = "branches"
    __table_args__ = (UniqueConstraint("network_id", "name"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    network_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("networks.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(200))
    city: Mapped[str] = mapped_column(String(100), default="")
    region: Mapped[str] = mapped_column(String(100), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    phone: Mapped[str] = mapped_column(String(50), default="")
    timezone: Mapped[str] = mapped_column(String(100), default="Europe/Moscow")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    network: Mapped[Network] = relationship(back_populates="branches", lazy="selectin")
    doctors: Mapped[list["Doctor"]] = relationship(
        back_populates="branch", lazy="selectin"
    )

    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    def local_to_utc(self, local_dt: datetime) -> datetime:
        """Наивное локальное время филиала → UTC."""
        return local_dt.replace(tzinfo=self.tz()).astimezone(UTC)

    def cancel_deadline(self, starts_at_utc: datetime, deadline_hours: int = 2) -> datetime:
        """UTC-момент, до которого пациент может сам отменить/перенести запись."""
        local = starts_at_utc.astimezone(self.tz())
        return (local - timedelta(hours=deadline_hours)).astimezone(UTC)


class Doctor(Base):
    """Врач. Личного кабинета нет — профилем и расписанием управляют администраторы."""

    __tablename__ = "doctors"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id", ondelete="CASCADE"))
    full_name: Mapped[str] = mapped_column(String(300))
    specialty: Mapped[str] = mapped_column(String(200), default="")
    photo_path: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    branch: Mapped[Branch] = relationship(back_populates="doctors", lazy="selectin")
    services: Mapped[list["Service"]] = relationship(
        secondary="doctor_services", lazy="selectin"
    )


class Service(Base):
    """Услуга/специальность. Длительность приёма определяется услугой."""

    __tablename__ = "services"
    __table_args__ = (UniqueConstraint("network_id", "name"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    network_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("networks.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(200))
    duration_minutes: Mapped[int] = mapped_column()
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DoctorService(Base):
    """Какие услуги оказывает врач."""

    __tablename__ = "doctor_services"

    doctor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("doctors.id", ondelete="CASCADE"), primary_key=True
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), primary_key=True
    )
