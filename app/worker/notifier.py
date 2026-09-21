"""Отправка очереди уведомлений.

Worker — отдельный singleton-процесс: напоминания не должны запускаться
в каждом web-воркере, иначе пользователь получит дубли.
"""
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment
from app.models.catalog import Branch, Doctor, Service
from app.models.notification import Notification
from app.models.schedule import Slot
from app.models.service import ServiceHeartbeat
from app.models.user import User
from app.services.notifications import REMINDER_KINDS, render_message

logger = logging.getLogger(__name__)


class MessageSender(Protocol):
    """Минимум, который нужен от бота (упрощает тесты)."""

    async def send_message(self, chat_id: int, text: str) -> object: ...


@dataclass
class DispatchResult:
    sent: int = 0
    skipped: int = 0
    failed: int = 0


async def write_heartbeat(session: AsyncSession, name: str = "worker") -> None:
    """Отмечает, что worker жив — читает публичная status page."""
    now = datetime.now(UTC)
    await session.execute(
        pg_insert(ServiceHeartbeat)
        .values(name=name, updated_at=now)
        .on_conflict_do_update(index_elements=[ServiceHeartbeat.name], set_={"updated_at": now})
    )
    await session.commit()


async def dispatch_pending_notifications(
    session: AsyncSession,
    sender: MessageSender,
    limit: int = 100,
) -> DispatchResult:
    """Отправляет готовые уведомления и гасит лишние напоминания.

    1. Напоминания отменённых/перенесённых записей переводятся в skipped —
       иначе пациент получил бы напоминание об отменённом приёме.
    2. Пending-уведомления с scheduled_for <= now отправляются по одному.
    """
    now = datetime.now(UTC)
    result = DispatchResult()

    stale = (
        await session.execute(
            select(Notification)
            .join(Appointment, Notification.appointment_id == Appointment.id)
            .where(
                Notification.status == "pending",
                Notification.kind.in_(REMINDER_KINDS),
                Appointment.status != "active",
            )
        )
    ).scalars().all()
    for notification in stale:
        notification.status = "skipped"
        notification.error = "Запись отменена или перенесена"
        result.skipped += 1

    rows = (
        await session.execute(
            select(Notification, Appointment, Slot, Doctor, Service, Branch, User)
            .join(Appointment, Notification.appointment_id == Appointment.id)
            .join(Slot, Appointment.slot_id == Slot.id)
            .join(Doctor, Slot.doctor_id == Doctor.id)
            .join(Service, Slot.service_id == Service.id)
            .join(Branch, Doctor.branch_id == Branch.id)
            .join(User, Notification.user_id == User.id)
            .where(Notification.status == "pending", Notification.scheduled_for <= now)
            .order_by(Notification.scheduled_for)
            .limit(limit)
        )
    ).all()

    for notification, appointment, slot, doctor, service, branch, user in rows:
        text = render_message(
            notification.kind,
            doctor_name=doctor.full_name,
            service_name=service.name,
            branch_name=branch.name,
            branch_address=branch.address,
            branch_phone=branch.phone,
            starts_at=slot.starts_at,
            timezone_name=branch.timezone,
        )
        try:
            await sender.send_message(user.telegram_id, text)
        except TelegramForbiddenError:
            notification.status = "failed"
            notification.error = "Пользователь не начал диалог с ботом или заблокировал его"
            result.failed += 1
        except TelegramAPIError as exc:
            notification.status = "failed"
            notification.error = str(exc)[:500]
            result.failed += 1
        else:
            notification.status = "sent"
            notification.sent_at = now
            result.sent += 1
            logger.info(
                "Уведомление отправлено kind=%s appointment_id=%s",
                notification.kind,
                appointment.id,
            )

        await session.commit()

    await session.commit()
    return result
