"""API пациентов: список, создание, удаление (нужна Postgres)."""
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.patients import router as patients_router
from app.core.deps import get_current_user
from app.db import get_session
from app.models.catalog import Branch, Doctor, Network, Service
from app.models.patient import Patient
from app.models.schedule import Slot
from app.models.user import User
from app.services.booking import book_slot


@pytest.fixture
async def client(db_session: AsyncSession) -> httpx.AsyncClient:
    user = User(telegram_id=999, first_name="Тест", role="patient")
    db_session.add(user)
    await db_session.commit()

    application = FastAPI()
    application.include_router(patients_router)

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    async def override_user() -> User:
        return user

    application.dependency_overrides[get_session] = override_session
    application.dependency_overrides[get_current_user] = override_user

    transport = httpx.ASGITransport(app=application)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def test_create_list_and_delete_patient(client: httpx.AsyncClient) -> None:
    created = await client.post(
        "/patients", json={"full_name": "Иванов Иван", "birth_date": "1990-01-02"}
    )
    assert created.status_code == 201
    patient_id = created.json()["id"]

    listed = await client.get("/patients")
    assert listed.status_code == 200
    assert any(row["id"] == patient_id for row in listed.json())

    deleted = await client.delete(f"/patients/{patient_id}")
    assert deleted.status_code == 204

    listed_after = await client.get("/patients")
    assert all(row["id"] != patient_id for row in listed_after.json())


async def test_delete_foreign_patient_returns_404(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    foreign_user = User(telegram_id=1001, role="patient")
    db_session.add(foreign_user)
    await db_session.flush()
    foreign = Patient(user_id=foreign_user.id, full_name="Чужой")
    db_session.add(foreign)
    await db_session.commit()

    response = await client.delete(f"/patients/{foreign.id}")

    assert response.status_code == 404


async def test_cannot_delete_patient_with_active_appointments(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    """Защита истории: пациента с активной записью удалить нельзя."""
    network = Network(slug="del-test", name="Сеть")
    branch = Branch(network_id=network.id, name="Филиал")
    service = Service(network_id=network.id, name="Приём", duration_minutes=30)
    doctor = Doctor(branch_id=branch.id, full_name="Доктор")
    db_session.add_all([network, branch, service, doctor])
    await db_session.flush()

    now = datetime.now(UTC).replace(microsecond=0)
    slot = Slot(
        doctor_id=doctor.id,
        service_id=service.id,
        starts_at=now + timedelta(days=5),
        ends_at=now + timedelta(days=5, minutes=30),
    )
    db_session.add(slot)
    await db_session.commit()

    created = await client.post("/patients", json={"full_name": "Петров Пётр"})
    patient_id = uuid.UUID(created.json()["id"])

    user = await db_session.get(User, 999)
    person = await db_session.get(Patient, patient_id)
    assert user is not None and person is not None
    await book_slot(db_session, user, person, slot.id)

    response = await client.delete(f"/patients/{patient_id}")

    assert response.status_code == 409
