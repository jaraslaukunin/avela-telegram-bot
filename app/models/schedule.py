import uuid
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Time,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.catalog import Doctor, Service


class ScheduleTemplate(Base):
    """Регулярный шаблон графика врача. Время — локальное время филиала.

    Два режима расписания (по требованиям): разовые слоты создаются
    напрямую в `slots`, регулярные графики — через этот шаблон
    с генерацией слотов (`generate_slots`).
    """

    __tablename__ = "schedule_templates"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("doctors.id", ondelete="CASCADE")
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE")
    )
    weekday: Mapped[int] = mapped_column(Integer)  # 0=Пн ... 6=Вс (ISO)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    valid_from: Mapped[date] = mapped_column(Date)
    valid_until: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def generate_slots(
        self,
        from_date: date,
        to_date: date,
        duration_minutes: int,
        tz: ZoneInfo,
        price: Decimal | None = None,
    ) -> list["Slot"]:
        """Генерирует слоты по шаблону на интервал дат включительно.

        Время шаблона трактуется в таймзоне филиала; в БД слоты кладутся
        в UTC. Длительность слота — из услуги (duration_minutes).
        """
        slots: list[Slot] = []
        current = max(from_date, self.valid_from)
        until = to_date if self.valid_until is None else min(to_date, self.valid_until)
        step = timedelta(minutes=duration_minutes)

        while current <= until:
            if current.weekday() == self.weekday:
                start = datetime.combine(current, self.start_time, tzinfo=tz)
                end = datetime.combine(current, self.end_time, tzinfo=tz)
                cursor = start
                while cursor + step <= end:
                    slots.append(
                        Slot(
                            doctor_id=self.doctor_id,
                            service_id=self.service_id,
                            starts_at=cursor.astimezone(UTC),
                            ends_at=(cursor + step).astimezone(UTC),
                            price=price,
                        )
                    )
                    cursor += step
            current += timedelta(days=1)

        return slots


class Slot(Base):
    """Слот: врач + услуга + интервал времени (UTC)."""

    __tablename__ = "slots"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("doctors.id", ondelete="CASCADE")
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("services.id", ondelete="RESTRICT")
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    doctor: Mapped["Doctor"] = relationship(lazy="selectin")
    service: Mapped["Service"] = relationship(lazy="selectin")

    def overlaps(self, other: "Slot") -> bool:
        """Пересечение интервалов [start, end)."""
        return self.starts_at < other.ends_at and other.starts_at < self.ends_at
