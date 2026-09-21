"""Тесты анонимизации аккаунта по запросу пациента (нужна Postgres)."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment
from app.models.notification import Notification
from app.models.user import AuditLog, User
from app.services.booking import book_slot
from app.services.privacy import anonymize_user


async def test_anonymize_cancels_appointments_and_scrubs_pii(
    db_session: AsyncSession, booking_catalog: dict[str, uuid.UUID]
) -> None:
    patient = await db_session.get(User, booking_catalog["patient_id"])
    assert patient is not None

    patient.username = "test_user"
    patient.phone = "+375 29 000-00-00"
    await db_session.commit()
    original_telegram_id = patient.telegram_id

    appointment = await book_slot(db_session, patient, booking_catalog["far_slot_id"])

    report = await anonymize_user(db_session, patient)

    assert report.cancelled_appointments == 1
    assert report.skipped_notifications == 3

    await db_session.refresh(appointment)
    assert appointment.status == "cancelled"
    assert appointment.cancelled_by == "patient"

    await db_session.refresh(patient)
    assert patient.first_name == ""
    assert patient.last_name == ""
    assert patient.username is None
    assert patient.phone is None
    assert patient.language_code is None
    assert patient.is_active is False
    assert patient.telegram_id != original_telegram_id
    assert patient.telegram_id < 0

    audit_rows = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.action == "user.anonymize")
        )
    ).scalars().all()
    assert len(audit_rows) == 1
    assert audit_rows[0].entity_id == patient.id


async def test_anonymized_user_keeps_appointment_history(
    db_session: AsyncSession, booking_catalog: dict[str, uuid.UUID]
) -> None:
    patient = await db_session.get(User, booking_catalog["patient_id"])
    assert patient is not None
    appointment = await book_slot(db_session, patient, booking_catalog["far_slot_id"])

    await anonymize_user(db_session, patient)

    # История записей остаётся обезличенной — клинике нужна статистика.
    stored = await db_session.get(Appointment, appointment.id)
    assert stored is not None
    assert stored.status == "cancelled"

    notifications = (
        await db_session.execute(
            select(Notification).where(Notification.appointment_id == appointment.id)
        )
    ).scalars().all()
    assert len(notifications) == 3
    assert all(row.status == "skipped" for row in notifications)
