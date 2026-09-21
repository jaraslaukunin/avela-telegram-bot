"""Очередь уведомлений в Telegram.

Отправкой занимается отдельный worker; здесь — только постановка в очередь.
Дедупликация гарантируется уникальным индексом (appointment_id, kind) в БД.
"""
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment
from app.models.notification import Notification
from app.models.schedule import Slot

BOOKING_CREATED = "booking_created"
REMINDER_24H = "reminder_24h"
REMINDER_2H = "reminder_2h"
CANCELLED = "cancelled"
RESCHEDULED = "rescheduled"


def enqueue_booking_notifications(
    session: AsyncSession,
    appointment: Appointment,
    slot: Slot,
) -> None:
    """Сразу после записи + напоминания за 24ч и за 2ч до приёма."""
    now = datetime.now(UTC)
    for kind, scheduled_for in (
        (BOOKING_CREATED, now),
        (REMINDER_24H, slot.starts_at - timedelta(hours=24)),
        (REMINDER_2H, slot.starts_at - timedelta(hours=2)),
    ):
        session.add(
            Notification(
                user_id=appointment.patient_id,
                appointment_id=appointment.id,
                kind=kind,
                scheduled_for=scheduled_for,
            )
        )


def enqueue_cancel_notification(
    session: AsyncSession,
    appointment: Appointment,
) -> None:
    session.add(
        Notification(
            user_id=appointment.patient_id,
            appointment_id=appointment.id,
            kind=CANCELLED,
            scheduled_for=datetime.now(UTC),
        )
    )


def enqueue_reschedule_notification(
    session: AsyncSession,
    appointment: Appointment,
    slot: Slot,
) -> None:
    session.add(
        Notification(
            user_id=appointment.patient_id,
            appointment_id=appointment.id,
            kind=RESCHEDULED,
            scheduled_for=datetime.now(UTC),
        )
    )
