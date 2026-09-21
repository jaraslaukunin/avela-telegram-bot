"""Use case'ы бронирования: вся бизнес-логика записи/отмены/переноса.

Хендлеры и API не содержат этой логики — только вызывают сервис.
Гарантии на уровне PostgreSQL (уникальные индексы, триггеры) защищают
от гонок; здесь — понятные ошибки и доменные проверки.
"""
import uuid
from datetime import UTC, datetime

from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment
from app.models.catalog import Branch, Doctor, Service
from app.models.schedule import Slot
from app.models.user import User
from app.services import audit, notifications

AppointmentContext = tuple[Appointment, Slot, Doctor, Service, Branch]


class BookingError(Exception):
    """Бизнес-ошибка бронирования — текст можно показывать пользователю."""


class SlotUnavailableError(BookingError):
    pass


class AppointmentNotFoundError(BookingError):
    pass


class DeadlinePassedError(BookingError):
    pass


async def _fetch_appointment_context(
    session: AsyncSession,
    appointment_id: uuid.UUID,
    patient_id: uuid.UUID | None = None,
) -> AppointmentContext | None:
    stmt = (
        select(Appointment, Slot, Doctor, Service, Branch)
        .join(Slot, Appointment.slot_id == Slot.id)
        .join(Doctor, Slot.doctor_id == Doctor.id)
        .join(Branch, Doctor.branch_id == Branch.id)
        .join(Service, Slot.service_id == Service.id)
        .where(Appointment.id == appointment_id)
    )
    if patient_id is not None:
        stmt = stmt.where(Appointment.patient_id == patient_id)

    row = (await session.execute(stmt)).one_or_none()
    if row is None:
        return None
    return row[0], row[1], row[2], row[3], row[4]


async def get_appointment_context(
    session: AsyncSession,
    patient_id: uuid.UUID,
    appointment_id: uuid.UUID,
) -> AppointmentContext | None:
    return await _fetch_appointment_context(session, appointment_id, patient_id)


async def get_appointment_context_for_admin(
    session: AsyncSession,
    appointment_id: uuid.UUID,
) -> AppointmentContext | None:
    """Контекст записи без фильтра по пациенту — для административных действий."""
    return await _fetch_appointment_context(session, appointment_id)


async def _ensure_no_patient_overlap(
    session: AsyncSession,
    patient_id: uuid.UUID,
    slot: Slot,
) -> None:
    """Явная проверка пересечения записей пациента (дублируется триггером в БД)."""
    patient_slots = (
        await session.execute(
            select(Slot)
            .join(Appointment, Appointment.slot_id == Slot.id)
            .where(Appointment.patient_id == patient_id, Appointment.status == "active")
        )
    ).scalars().all()

    if any(slot.overlaps(existing) for existing in patient_slots):
        raise BookingError("У вас уже есть запись на пересекающееся время")


async def book_slot(
    session: AsyncSession,
    patient: User,
    slot_id: uuid.UUID,
    patient_full_name: str | None = None,
) -> Appointment:
    """Запись на конкретный слот. Атомарно защищена уникальным индексом БД."""
    slot = await session.get(Slot, slot_id)
    if slot is None:
        raise SlotUnavailableError("Слот не найден")

    taken = await session.scalar(
        select(Appointment.id).where(
            Appointment.slot_id == slot_id,
            Appointment.status == "active",
        )
    )
    if taken is not None:
        raise SlotUnavailableError("Слот уже занят")

    await _ensure_no_patient_overlap(session, patient.id, slot)

    appointment = Appointment(
        patient_id=patient.id,
        slot_id=slot_id,
        status="active",
        patient_full_name=patient_full_name,
    )
    session.add(appointment)

    try:
        await session.flush()  # присваивает id
    except IntegrityError as exc:
        # Гонка: слот заняли параллельно или сработал триггер пересечений.
        await session.rollback()
        raise SlotUnavailableError(
            "Не удалось создать запись: слот уже занят "
            "или пересекается с вашей другой записью"
        ) from exc

    notifications.enqueue_booking_notifications(session, appointment, slot)
    await session.commit()
    return appointment


async def cancel_appointment(
    session: AsyncSession,
    patient_id: uuid.UUID,
    appointment_id: uuid.UUID,
    now_utc: datetime | None = None,
) -> Appointment:
    """Самостоятельная отмена: только раньше чем за 2 часа до приёма."""
    now = now_utc or datetime.now(UTC)
    context = await get_appointment_context(session, patient_id, appointment_id)
    if context is None:
        raise AppointmentNotFoundError("Запись не найдена")

    appointment, _slot, _doctor, _service, branch = context

    if not appointment.is_active:
        raise BookingError("Запись уже отменена или перенесена")

    if not appointment.is_cancellable_by_patient(branch, now):
        raise DeadlinePassedError(
            "Самостоятельная отмена недоступна менее чем за 2 часа до приёма. "
            f"Обратитесь в клинику: {branch.phone or branch.name}"
        )

    appointment.cancel("patient", now)
    notifications.enqueue_cancel_notification(session, appointment)
    await session.commit()
    return appointment


async def cancel_appointment_by_admin(
    session: AsyncSession,
    actor: User,
    appointment_id: uuid.UUID,
    now_utc: datetime | None = None,
) -> Appointment:
    """Отмена администратором: без ограничения 2 часов, с записью в аудит."""
    now = now_utc or datetime.now(UTC)
    context = await _fetch_appointment_context(session, appointment_id)
    if context is None:
        raise AppointmentNotFoundError("Запись не найдена")

    appointment, slot, _doctor, _service, branch = context
    if not appointment.is_active:
        raise BookingError("Запись уже отменена или перенесена")

    appointment.cancel("admin", now)
    notifications.enqueue_cancel_notification(session, appointment)
    audit.write_audit(
        session,
        actor,
        "appointment.cancel",
        entity_type="appointment",
        entity_id=appointment.id,
        network_id=branch.network_id,
        details={"slot_id": str(slot.id), "branch_id": str(branch.id)},
    )
    await session.commit()
    return appointment


async def reschedule_appointment(
    session: AsyncSession,
    patient_id: uuid.UUID,
    appointment_id: uuid.UUID,
    new_slot_id: uuid.UUID,
    now_utc: datetime | None = None,
) -> Appointment:
    """Перенос: тот же дедлайн, старый слот освобождается, новый бронируется."""
    now = now_utc or datetime.now(UTC)
    context = await get_appointment_context(session, patient_id, appointment_id)
    if context is None:
        raise AppointmentNotFoundError("Запись не найдена")

    appointment, _old_slot, _doctor, _service, branch = context

    if not appointment.is_active:
        raise BookingError("Запись уже отменена или перенесена")

    if not appointment.is_cancellable_by_patient(branch, now):
        raise DeadlinePassedError(
            "Самостоятельный перенос недоступен менее чем за 2 часа до приёма. "
            f"Обратитесь в клинику: {branch.phone or branch.name}"
        )

    new_slot = await session.get(Slot, new_slot_id)
    if new_slot is None:
        raise SlotUnavailableError("Новый слот не найден")

    await _ensure_no_patient_overlap(session, patient_id, new_slot)

    new_appointment = Appointment(
        patient_id=patient_id,
        slot_id=new_slot.id,
        status="active",
        rescheduled_from_id=appointment.id,
        patient_full_name=appointment.patient_full_name,
    )
    appointment.status = "rescheduled"
    session.add(new_appointment)

    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise SlotUnavailableError(
            "Новый слот уже занят или пересекается с вашими записями"
        ) from exc

    notifications.enqueue_reschedule_notification(session, new_appointment, new_slot)
    await session.commit()
    return new_appointment


async def list_available_slots(
    session: AsyncSession,
    service_id: uuid.UUID,
    from_dt: datetime,
    to_dt: datetime,
    branch_id: uuid.UUID | None = None,
    doctor_id: uuid.UUID | None = None,
) -> list[tuple[Slot, Doctor, Branch]]:
    """Свободные слоты по услуге. «Любой свободный врач» = выбор без doctor_id."""
    stmt = (
        select(Slot, Doctor, Branch)
        .join(Doctor, Slot.doctor_id == Doctor.id)
        .join(Branch, Doctor.branch_id == Branch.id)
        .where(
            Slot.service_id == service_id,
            Slot.starts_at >= from_dt,
            Slot.starts_at < to_dt,
            Doctor.is_active.is_(True),
            Branch.is_active.is_(True),
            ~exists(
                select(Appointment.id).where(
                    Appointment.slot_id == Slot.id,
                    Appointment.status == "active",
                )
            ),
        )
        .order_by(Slot.starts_at)
    )
    if branch_id is not None:
        stmt = stmt.where(Branch.id == branch_id)
    if doctor_id is not None:
        stmt = stmt.where(Slot.doctor_id == doctor_id)

    rows = (await session.execute(stmt)).all()
    return [(row[0], row[1], row[2]) for row in rows]
