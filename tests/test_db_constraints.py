import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment
from app.models.catalog import Branch, Doctor, Network, Service
from app.models.schedule import Slot
from app.models.user import User

NOW = datetime.now(UTC).replace(microsecond=0)


async def _create_catalog(
    session: AsyncSession,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    network = Network(slug="test", name="Тестовая сеть")
    session.add(network)
    await session.flush()

    branch = Branch(network_id=network.id, name="Филиал 1")
    session.add(branch)
    await session.flush()

    patient = User(telegram_id=101, first_name="Пациент", role="patient")
    doctor = Doctor(branch_id=branch.id, full_name="Доктор Айболит")
    doctor2 = Doctor(branch_id=branch.id, full_name="Доктор Борменталь")
    service = Service(network_id=network.id, name="Приём терапевта", duration_minutes=30)
    session.add_all([patient, doctor, doctor2, service])
    await session.flush()

    return network.id, branch.id, patient.id, doctor.id, doctor2.id, service.id


async def test_catalog_roundtrip(db_session: AsyncSession) -> None:
    ids = await _create_catalog(db_session)
    network_id, branch_id, patient_id, doctor_id, doctor2_id, service_id = ids

    assert all(isinstance(value, uuid.UUID) for value in ids)
    assert network_id != branch_id
    assert patient_id != doctor_id
    assert doctor_id != doctor2_id
    assert service_id != network_id


async def test_slot_overlap_same_doctor_rejected(db_session: AsyncSession) -> None:
    ids = await _create_catalog(db_session)
    doctor_id, service_id = ids[3], ids[5]

    slot1 = Slot(
        doctor_id=doctor_id,
        service_id=service_id,
        starts_at=NOW + timedelta(hours=1),
        ends_at=NOW + timedelta(hours=1, minutes=30),
    )
    slot2 = Slot(
        doctor_id=doctor_id,
        service_id=service_id,
        starts_at=NOW + timedelta(hours=1, minutes=15),
        ends_at=NOW + timedelta(hours=1, minutes=45),
    )
    db_session.add_all([slot1, slot2])

    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_double_booking_same_slot_rejected(db_session: AsyncSession) -> None:
    ids = await _create_catalog(db_session)
    patient_id, doctor_id, service_id = ids[2], ids[3], ids[5]

    slot = Slot(
        doctor_id=doctor_id,
        service_id=service_id,
        starts_at=NOW + timedelta(hours=2),
        ends_at=NOW + timedelta(hours=2, minutes=30),
    )
    db_session.add(slot)
    await db_session.flush()

    db_session.add(Appointment(patient_id=patient_id, slot_id=slot.id, status="active"))
    await db_session.flush()

    db_session.add(Appointment(patient_id=patient_id, slot_id=slot.id, status="active"))

    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_patient_overlap_across_doctors_rejected(db_session: AsyncSession) -> None:
    ids = await _create_catalog(db_session)
    patient_id, doctor_id, doctor2_id, service_id = ids[2], ids[3], ids[4], ids[5]

    slot_a = Slot(
        doctor_id=doctor_id,
        service_id=service_id,
        starts_at=NOW + timedelta(hours=3),
        ends_at=NOW + timedelta(hours=3, minutes=30),
    )
    slot_b = Slot(
        doctor_id=doctor2_id,
        service_id=service_id,
        starts_at=NOW + timedelta(hours=3, minutes=10),
        ends_at=NOW + timedelta(hours=3, minutes=40),
    )
    db_session.add_all([slot_a, slot_b])
    await db_session.flush()

    db_session.add(Appointment(patient_id=patient_id, slot_id=slot_a.id, status="active"))
    await db_session.flush()

    db_session.add(Appointment(patient_id=patient_id, slot_id=slot_b.id, status="active"))

    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_patient_non_overlapping_appointments_ok(db_session: AsyncSession) -> None:
    ids = await _create_catalog(db_session)
    patient_id, doctor_id, service_id = ids[2], ids[3], ids[5]

    slot_a = Slot(
        doctor_id=doctor_id,
        service_id=service_id,
        starts_at=NOW + timedelta(hours=4),
        ends_at=NOW + timedelta(hours=4, minutes=30),
    )
    slot_b = Slot(
        doctor_id=doctor_id,
        service_id=service_id,
        starts_at=NOW + timedelta(hours=4, minutes=30),
        ends_at=NOW + timedelta(hours=5),
    )
    db_session.add_all([slot_a, slot_b])
    await db_session.flush()

    db_session.add_all(
        [
            Appointment(patient_id=patient_id, slot_id=slot_a.id, status="active"),
            Appointment(patient_id=patient_id, slot_id=slot_b.id, status="active"),
        ]
    )

    await db_session.flush()


async def test_cancelled_appointment_does_not_block_slot(db_session: AsyncSession) -> None:
    ids = await _create_catalog(db_session)
    patient_id, doctor_id, service_id = ids[2], ids[3], ids[5]

    slot = Slot(
        doctor_id=doctor_id,
        service_id=service_id,
        starts_at=NOW + timedelta(hours=5),
        ends_at=NOW + timedelta(hours=5, minutes=30),
    )
    db_session.add(slot)
    await db_session.flush()

    cancelled = Appointment(
        patient_id=patient_id,
        slot_id=slot.id,
        status="cancelled",
        cancelled_by="patient",
        cancelled_at=NOW,
    )
    db_session.add(cancelled)
    await db_session.flush()

    # Отменённая запись не блокирует слот — новая активная запись проходит.
    db_session.add(Appointment(patient_id=patient_id, slot_id=slot.id, status="active"))
    await db_session.flush()
