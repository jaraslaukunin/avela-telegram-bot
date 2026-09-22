import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class Patient(Base):
    """Пациент: человек, которого записывают на приём.

    Один Telegram-аккаунт (users) может вести нескольких пациентов —
    например, родитель записывает себя и детей. Пересечения приёмов
    считаются на уровне пациента, а не аккаунта.
    """

    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    full_name: Mapped[str] = mapped_column(String(300))
    birth_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship(lazy="selectin")

    @property
    def is_child(self) -> bool:
        """Ребёнок — до 18 лет. Используется для фильтра взрослый/детский."""
        if self.birth_date is None:
            return False
        today = date.today()
        years = (
            today.year
            - self.birth_date.year
            - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        )
        return years < 18
