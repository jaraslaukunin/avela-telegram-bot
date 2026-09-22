"""Тесты worker'а уведомлений (нужна Postgres)."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment
from app.models.notification import Notification
from app.models.patient import Patient
from app.models.user import User
from app.services.booking import book_slot, cancel_appointment
from app.worker.notifier import dispatch_pending_notifications


class FakeSender:
    """Заглушка бота: запоминает отправленные сообщения."""

    def __init__(self) -> None:
        self.sent: list[tuple[int, str]] = []

    async def send_message(self, chat_id: int, text: str) -> None:
        self.sent.append((chat_id, text))


async def _book(
    session: AsyncSession,
    catalog: dict[str, uuid.UUID],
    slot_key: str,
) -> Appointment:
    """Бронирует слот за пациента по умолчанию (владельца аккаунта)."""
    user = await session.get(User, catalog["patient_id"])
    person = await session.get(Patient, catalog["patient_profile_id"])
    assert user is not None and person is not None
    return await book_slot(session, user, person, catalog[slot_key])


async def _statuses(session: AsyncSession, appointment_id: uuid.UUID) -> dict[str, str]:
    rows = (
        await session.execute(
            select(Notification.kind, Notification.status).where(
                Notification.appointment_id == appointment_id
            )
        )
    ).all()
    return {kind: status for kind, status in rows}


async def test_immediate_notification_is_sent_once(
    db_session: AsyncSession, booking_catalog: dict[str, uuid.UUID]
) -> None:
    appointment = await _book(db_session, booking_catalog, "far_slot_id")

    sender = FakeSender()
    result = await dispatch_pending_notifications(db_session, sender)

    # Слот через 7 дней: отправляется только подтверждение записи,
    # напоминания остаются в очереди.
    assert result.sent == 1
    assert "Запись создана" in sender.sent[0][1]

    statuses = await _statuses(db_session, appointment.id)
    assert statuses["booking_created"] == "sent"
    assert statuses["reminder_24h"] == "pending"
    assert statuses["reminder_2h"] == "pending"


    # Повторный запуск не отправляет то же самое второй раз (дедупликация).
    second_sender = FakeSender()
    second_result = await dispatch_pending_notifications(db_session, second_sender)
    assert second_result.sent == 0
    assert second_sender.sent == []


async def test_past_reminders_are_not_enqueued(
    db_session: AsyncSession, booking_catalog: dict[str, uuid.UUID]
) -> None:
    # Слот через час: напоминание за 24 часа и за 2 часа уже в прошлом.
    appointment = await _book(db_session, booking_catalog, "urgent_slot_id")

    statuses = await _statuses(db_session, appointment.id)
    assert statuses["reminder_24h"] == "skipped"
    assert statuses["reminder_2h"] == "skipped"

    sender = FakeSender()
    result = await dispatch_pending_notifications(db_session, sender)

    assert result.sent == 1
    assert len(sender.sent) == 1


async def test_cancelled_appointment_reminders_are_skipped(
    db_session: AsyncSession, booking_catalog: dict[str, uuid.UUID]
) -> None:
    patient = await db_session.get(User, booking_catalog["patient_id"])
    assert patient is not None

    appointment = await _book(db_session, booking_catalog, "far_slot_id")
    await cancel_appointment(db_session, patient.id, appointment.id)

    sender = FakeSender()
    result = await dispatch_pending_notifications(db_session, sender)

    # Отправляются подтверждение записи и уведомление об отмене.
    assert result.sent == 2
    texts = " ".join(text for _chat_id, text in sender.sent)
    assert "Запись создана" in texts
    assert "Запись отменена" in texts

    # Напоминания отменённой записи не уходят.
    statuses = await _statuses(db_session, appointment.id)
    assert statuses["reminder_24h"] == "skipped"
    assert statuses["reminder_2h"] == "skipped"
