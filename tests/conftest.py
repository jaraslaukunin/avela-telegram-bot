import os
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.catalog import Branch, Doctor, Network, Service
from app.models.patient import Patient
from app.models.schedule import Slot
from app.models.user import User

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "")

TABLES = (
    "notifications",
    "service_heartbeats",
    "patients",
    "appointments",
    "slots",
    "schedule_templates",
    "doctor_services",
    "branch_admins",
    "doctors",
    "services",
    "branches",
    "users",
    "networks",
    "audit_logs",
)


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Сессия к тестовой БД с очисткой всех таблиц.

    Пропускает тесты, если TEST_DATABASE_URL не задан (например, локально
    без поднятой Postgres).
    """
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL не задан — интеграционные тесты пропущены")

    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as connection:
        await connection.execute(
            text(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY CASCADE")
        )

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def booking_catalog(db_session: AsyncSession) -> dict[str, uuid.UUID]:
    """Сеть + филиал + услуга + два врача + два пациента + слоты вокруг NOW."""
    network = Network(slug="booking", name="Сеть бронирования")
    db_session.add(network)
    await db_session.flush()

    branch = Branch(network_id=network.id, name="Филиал", phone="+7 999 000-00-00")
    db_session.add(branch)
    await db_session.flush()

    service = Service(network_id=network.id, name="Приём", duration_minutes=30)
    patient = User(telegram_id=101, first_name="Пациент 1", role="patient")
    patient2 = User(telegram_id=202, first_name="Пациент 2", role="patient")
    doctor = Doctor(branch_id=branch.id, full_name="Доктор Айболит")
    doctor2 = Doctor(branch_id=branch.id, full_name="Доктор Борменталь")
    db_session.add_all([service, patient, patient2, doctor, doctor2])
    await db_session.flush()

    person1 = Patient(user_id=patient.id, full_name="Пациент 1")
    person2 = Patient(user_id=patient2.id, full_name="Пациент 2")
    db_session.add_all([person1, person2])
    await db_session.flush()

    now = datetime.now(UTC).replace(microsecond=0)

    def slot(doctor: Doctor, start: datetime, end: datetime) -> Slot:
        return Slot(
            doctor_id=doctor.id, service_id=service.id, starts_at=start, ends_at=end
        )

    far_slot = slot(doctor, now + timedelta(days=7), now + timedelta(days=7, minutes=30))
    urgent_slot = slot(
        doctor2, now + timedelta(hours=1), now + timedelta(hours=1, minutes=30)
    )
    other_far_slot = slot(
        doctor2, now + timedelta(days=8), now + timedelta(days=8, minutes=30)
    )
    db_session.add_all([far_slot, urgent_slot, other_far_slot])
    await db_session.commit()

    return {
        "network_id": network.id,
        "branch_id": branch.id,
        "service_id": service.id,
        "patient_id": patient.id,
        "patient2_id": patient2.id,
        "patient_profile_id": person1.id,
        "patient2_profile_id": person2.id,
        "doctor_id": doctor.id,
        "doctor2_id": doctor2.id,
        "far_slot_id": far_slot.id,
        "urgent_slot_id": urgent_slot.id,
        "other_far_slot_id": other_far_slot.id,
    }
