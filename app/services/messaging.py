"""Сообщения пациентам из админки.

Администратор может написать пациенту (например, «врач задерживается»),
сообщение уходит в Telegram от имени бота. Права проверяются на уровне
роута (зона филиала), здесь — только отправка и аудит.
"""
import logging
import uuid

from aiogram.exceptions import TelegramForbiddenError
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.client import get_bot
from app.models.user import User
from app.services import audit
from app.services.booking import AppointmentNotFoundError, get_appointment_context_for_admin

logger = logging.getLogger(__name__)


class PatientUnreachableError(Exception):
    """Пациент не может получить сообщение (например, не открывал бота)."""


async def send_message_to_appointment_patient(
    session: AsyncSession,
    actor: User,
    appointment_id: uuid.UUID,
    text: str,
) -> None:
    """Отправляет сообщение пациенту записи от имени бота, пишет аудит."""
    context = await get_appointment_context_for_admin(session, appointment_id)
    if context is None:
        raise AppointmentNotFoundError("Запись не найдена")

    appointment, _slot, _doctor, _service, _branch = context
    patient = await session.get(User, appointment.patient_id)
    if patient is None:
        raise PatientUnreachableError("Пациент не найден")

    try:
        await get_bot().send_message(patient.telegram_id, f"🏥 <b>Avela</b>\n\n{text}")
    except TelegramForbiddenError as exc:
        raise PatientUnreachableError(
            "Пациент ещё не открывал бота — доставить сообщение нельзя"
        ) from exc

    audit.write_audit(
        session,
        actor,
        "appointment.message",
        entity_type="appointment",
        entity_id=appointment.id,
        details={"text_length": len(text)},
    )
    await session.commit()
    logger.info(
        "Сообщение пациенту appointment_id=%s actor=%s",
        appointment.id,
        actor.telegram_id,
    )
