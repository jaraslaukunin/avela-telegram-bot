"""Право на удаление: анонимизация персональных данных.

Сценарий (документирован в README):
1. Активные записи пациента отменяются — если человек удаляет данные,
   его приёмы не должны остаться в силе.
2. Незакрытые уведомления помечаются skipped (история отправок остаётся).
3. Персональные поля затираются, telegram_id заменяется служебным
   отрицательным, чтобы новое обращение создало новый аккаунт.
4. Аккаунт деактивируется, факт анонимизации пишется в audit_logs.

Клинических данных мы не храним, поэтому анонимизация ПДн == удаление.
"""
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment
from app.models.notification import Notification
from app.models.patient import Patient
from app.models.user import User
from app.services import audit


@dataclass(frozen=True)
class AnonymizationReport:
    cancelled_appointments: int
    skipped_notifications: int


async def anonymize_user(
    session: AsyncSession,
    user: User,
    actor: User | None = None,
) -> AnonymizationReport:
    now = datetime.now(UTC)

    active_appointments = (
        await session.execute(
            select(Appointment).where(
                Appointment.patient_id == user.id,
                Appointment.status == "active",
            )
        )
    ).scalars().all()
    for appointment in active_appointments:
        appointment.cancel("patient", now)

    pending_notifications = (
        await session.execute(
            select(Notification).where(
                Notification.user_id == user.id,
                Notification.status == "pending",
            )
        )
    ).scalars().all()
    for notification in pending_notifications:
        notification.status = "skipped"
        notification.error = "Пользователь удалил аккаунт"

    audit.write_audit(
        session,
        actor or user,
        "user.anonymize",
        entity_type="user",
        entity_id=user.id,
        details={
            "cancelled_appointments": len(active_appointments),
            "skipped_notifications": len(pending_notifications),
        },
    )

    # Профили пациентов аккаунта тоже содержат ПДн (ФИО, даты рождения).
    patients = (
        await session.execute(select(Patient).where(Patient.user_id == user.id))
    ).scalars().all()
    for patient in patients:
        patient.full_name = "Аноним"
        patient.birth_date = None

    user.first_name = ""
    user.last_name = ""
    user.username = None
    user.phone = None
    user.language_code = None
    user.is_active = False
    user.telegram_id = -(uuid.uuid4().int % 10**15) - 1

    await session.commit()
    return AnonymizationReport(
        cancelled_appointments=len(active_appointments),
        skipped_notifications=len(pending_notifications),
    )
