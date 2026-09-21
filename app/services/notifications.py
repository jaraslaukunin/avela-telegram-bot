"""Очередь уведомлений в Telegram и тексты сообщений.

Отправкой занимается отдельный worker (`app/worker`); здесь — постановка
в очередь и рендер текстов.
Дедупликация гарантируется уникальным индексом (appointment_id, kind) в БД.
"""
from datetime import UTC, datetime, timedelta, tzinfo
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment
from app.models.notification import Notification
from app.models.schedule import Slot

BOOKING_CREATED = "booking_created"
REMINDER_24H = "reminder_24h"
REMINDER_2H = "reminder_2h"
CANCELLED = "cancelled"
RESCHEDULED = "rescheduled"

REMINDER_KINDS = (REMINDER_24H, REMINDER_2H)


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
        in_future = scheduled_for >= now
        session.add(
            Notification(
                user_id=appointment.patient_id,
                appointment_id=appointment.id,
                kind=kind,
                scheduled_for=scheduled_for,
                # Запись «за час до приёма» не должна присылать напоминание
                # за 24 часа — момент уже прошёл, помечаем как пропущенное.
                status="pending" if in_future else "skipped",
                error=None if in_future else "Время уведомления уже прошло",
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


def format_local_time(starts_at: datetime, timezone_name: str) -> str:
    """Время приёма в часовом поясе филиала."""
    tz: tzinfo
    try:
        tz = ZoneInfo(timezone_name)
    except Exception:  # некорректная таймзона не должна ломать уведомление
        tz = UTC
    return starts_at.astimezone(tz).strftime("%d.%m.%Y %H:%M")


def render_message(
    kind: str,
    *,
    doctor_name: str,
    service_name: str,
    branch_name: str,
    branch_address: str,
    branch_phone: str,
    starts_at: datetime,
    timezone_name: str,
) -> str:
    """Текст уведомления. Чистая функция — тестируется без БД и Telegram."""
    when = format_local_time(starts_at, timezone_name)
    where = f"{branch_name}, {branch_address}" if branch_address else branch_name
    appointment_line = f"{service_name}, {doctor_name}\n{where}\n🗓 {when}"

    if kind == BOOKING_CREATED:
        return (
            "✅ <b>Запись создана</b>\n"
            f"{appointment_line}\n\n"
            "Отменить или перенести запись можно в «Моих записях» "
            "не позднее чем за 2 часа до приёма."
        )
    if kind == REMINDER_24H:
        return f"⏰ <b>Напоминание: приём завтра</b>\n{appointment_line}"
    if kind == REMINDER_2H:
        return f"⏰ <b>Напоминание: приём через 2 часа</b>\n{appointment_line}"
    if kind == CANCELLED:
        return (
            "❌ <b>Запись отменена</b>\n"
            f"{appointment_line}\n\n"
            f"Если это ошибка — позвоните в клинику: {branch_phone}"
        )
    if kind == RESCHEDULED:
        return (
            "🔄 <b>Запись перенесена</b>\n"
            f"{appointment_line}\n\n"
            "Если время не подходит — обратитесь в «Мои записи»."
        )

    return f"ℹ️ {appointment_line}"
