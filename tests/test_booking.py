"""Интеграционные тесты логики бронирования (нужна Postgres)."""
import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.appointment import Appointment
from app.models.catalog import Doctor
from app.models.notification import Notification
from app.models.schedule import Slot
from app.models.user import User
from app.services.booking import (
    AppointmentNotFoundError,
    BookingError,
    DeadlinePassedError,
    SlotUnavailableError,
    book_slot,
    cancel_appointment,
    list_available_slots,
    reschedule_appointment,
)
from tests.conftest import TEST_DATABASE_URL


async def _get_user(session: AsyncSession, user_id: uuid.UUID) -> User:
    user = await session.get(User, user_id)
    assert user is not None
    return user


async def _notification_kinds(session: AsyncSession, appointment_id: uuid.UUID) -> set[str]:
    kinds = (
        await session.execute(
            select(Notification.kind).where(Notification.appointment_id == appointment_id)
        )
    ).scalars().all()
    return set(kinds)


async def test_book_slot_creates_appointment_and_notifications(
    db_session: AsyncSession, booking_catalog: dict[str, uuid.UUID]
) -> None:
    patient = await _get_user(db_session, booking_catalog["patient_id"])

    appointment = await book_slot(db_session, patient, booking_catalog["far_slot_id"])

    assert appointment.status == "active"
    kinds = await _notification_kinds(db_session, appointment.id)
    assert kinds == {"booking_created", "reminder_24h", "reminder_2h"}


async def test_double_booking_rejected_with_clean_error(
    db_session: AsyncSession, booking_catalog: dict[str, uuid.UUID]
) -> None:
    patient1 = await _get_user(db_session, booking_catalog["patient_id"])
    patient2 = await _get_user(db_session, booking_catalog["patient2_id"])

    await book_slot(db_session, patient1, booking_catalog["far_slot_id"])

    with pytest.raises(SlotUnavailableError):
        await book_slot(db_session, patient2, booking_catalog["far_slot_id"])


async def test_patient_cannot_book_overlapping_slots(
    db_session: AsyncSession, booking_catalog: dict[str, uuid.UUID]
) -> None:
    patient = await _get_user(db_session, booking_catalog["patient_id"])

    await book_slot(db_session, patient, booking_catalog["far_slot_id"])
    await book_slot(db_session, patient, booking_catalog["other_far_slot_id"])

    # Третий слот у другого врача, пересекающийся с первым по времени.
    doctor2 = await db_session.get(Doctor, booking_catalog["doctor2_id"])
    assert doctor2 is not None
    now = datetime.now(UTC).replace(microsecond=0)
    conflict = Slot(
        doctor_id=doctor2.id,
        service_id=booking_catalog["service_id"],
        starts_at=now + timedelta(days=7, minutes=10),
        ends_at=now + timedelta(days=7, minutes=40),
    )
    db_session.add(conflict)
    await db_session.commit()

    with pytest.raises(BookingError):
        await book_slot(db_session, patient, conflict.id)


async def test_cancel_within_deadline(
    db_session: AsyncSession, booking_catalog: dict[str, uuid.UUID]
) -> None:
    patient = await _get_user(db_session, booking_catalog["patient_id"])

    appointment = await book_slot(db_session, patient, booking_catalog["far_slot_id"])
    cancelled = await cancel_appointment(db_session, patient.id, appointment.id)

    assert cancelled.status == "cancelled"
    assert cancelled.cancelled_by == "patient"
    kinds = await _notification_kinds(db_session, appointment.id)
    assert "cancelled" in kinds


async def test_cancel_after_deadline_rejected_with_phone(
    db_session: AsyncSession, booking_catalog: dict[str, uuid.UUID]
) -> None:
    patient = await _get_user(db_session, booking_catalog["patient_id"])

    appointment = await book_slot(db_session, patient, booking_catalog["urgent_slot_id"])

    with pytest.raises(DeadlinePassedError) as exc_info:
        await cancel_appointment(db_session, patient.id, appointment.id)

    assert "+7 999 000-00-00" in str(exc_info.value)


async def test_reschedule_moves_to_new_slot(
    db_session: AsyncSession, booking_catalog: dict[str, uuid.UUID]
) -> None:
    patient = await _get_user(db_session, booking_catalog["patient_id"])

    old_appointment = await book_slot(db_session, patient, booking_catalog["far_slot_id"])
    new_appointment = await reschedule_appointment(
        db_session, patient.id, old_appointment.id, booking_catalog["other_far_slot_id"]
    )

    assert new_appointment.status == "active"
    assert new_appointment.rescheduled_from_id == old_appointment.id
    assert new_appointment.slot_id == booking_catalog["other_far_slot_id"]

    await db_session.refresh(old_appointment)
    assert old_appointment.status == "rescheduled"

    # Старый слот снова свободен — его может занять другой пациент.
    patient2 = await _get_user(db_session, booking_catalog["patient2_id"])
    reopened = await book_slot(db_session, patient2, booking_catalog["far_slot_id"])
    assert reopened.status == "active"


async def test_cancel_nonexistent_appointment(
    db_session: AsyncSession, booking_catalog: dict[str, uuid.UUID]
) -> None:
    patient = await _get_user(db_session, booking_catalog["patient_id"])

    with pytest.raises(AppointmentNotFoundError):
        await cancel_appointment(db_session, patient.id, uuid.uuid4())


async def test_available_slots_exclude_booked(
    db_session: AsyncSession, booking_catalog: dict[str, uuid.UUID]
) -> None:
    patient = await _get_user(db_session, booking_catalog["patient_id"])
    await book_slot(db_session, patient, booking_catalog["far_slot_id"])

    now = datetime.now(UTC).replace(microsecond=0)
    rows = await list_available_slots(
        db_session,
        booking_catalog["service_id"],
        from_dt=now - timedelta(days=1),
        to_dt=now + timedelta(days=30),
    )

    slot_ids = {slot.id for slot, _doctor, _branch in rows}
    assert booking_catalog["far_slot_id"] not in slot_ids
    assert booking_catalog["urgent_slot_id"] in slot_ids
    assert booking_catalog["other_far_slot_id"] in slot_ids


async def test_race_two_patients_one_slot(
    booking_catalog: dict[str, uuid.UUID],
) -> None:
    """Гонка: два пациента одновременно бронируют один слот — выигрывает ровно один."""
    engine = create_async_engine(TEST_DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def attempt(patient_id: uuid.UUID) -> bool:
        async with factory() as session:
            patient = await session.get(User, patient_id)
            assert patient is not None
            try:
                await book_slot(session, patient, booking_catalog["far_slot_id"])
            except BookingError:
                return False
            return True

    results = await asyncio.gather(
        attempt(booking_catalog["patient_id"]),
        attempt(booking_catalog["patient2_id"]),
    )

    assert results.count(True) == 1

    async with factory() as session:
        active = (
            await session.execute(
                select(Appointment).where(
                    Appointment.slot_id == booking_catalog["far_slot_id"],
                    Appointment.status == "active",
                )
            )
        ).scalars().all()
        assert len(active) == 1

    await engine.dispose()
