import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.catalog import Branch
from app.models.schedule import Slot
from app.models.user import User


class Appointment(Base):
    """Запись на приём. Статусы: active, cancelled, completed, rescheduled."""

    PATIENT_CANCEL_DEADLINE_HOURS = 2

    __tablename__ = "appointments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    slot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("slots.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(30), default="active")
    patient_full_name: Mapped[str | None] = mapped_column(String(300))
    rescheduled_from_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("appointments.id")
    )
    cancelled_by: Mapped[str | None] = mapped_column(String(20))
    cancelled_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    slot: Mapped[Slot] = relationship(lazy="selectin")
    patient: Mapped[User] = relationship(lazy="selectin")

    @property
    def is_active(self) -> bool:
        return self.status == "active"

    def is_cancellable_by_patient(self, branch: "Branch", now_utc: datetime) -> bool:
        """Самостоятельная отмена доступна строго раньше дедлайна.

        Дедлайн = приём минус 2 часа в таймзоне филиала.
        """
        deadline = branch.cancel_deadline(
            self.slot.starts_at,
            deadline_hours=self.PATIENT_CANCEL_DEADLINE_HOURS,
        )
        return now_utc < deadline

    def cancel(self, by: str, at: datetime) -> None:
        """Отмена записи: фиксируем кто и когда (для аудита)."""
        self.status = "cancelled"
        self.cancelled_by = by
        self.cancelled_at = at
