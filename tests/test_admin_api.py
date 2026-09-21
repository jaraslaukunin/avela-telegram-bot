"""Интеграционные тесты админ-API: роли, изоляция сетей, расписание, отмена."""
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_appointments import router as admin_appointments_router
from app.api.admin_catalog import router as admin_catalog_router
from app.core.roles import (
    ROLE_AVELA_ADMIN,
    ROLE_BRANCH_ADMIN,
    ROLE_NETWORK_ADMIN,
    ROLE_PATIENT,
)
from app.core.security.jwt import create_session_token
from app.db import get_session
from app.models.catalog import Branch, Doctor, Network, Service
from app.models.schedule import Slot
from app.models.user import AuditLog, BranchAdmin, User
from app.services.booking import book_slot

SECRET = "integration-test-secret-0123456789"


@pytest_asyncio.fixture
async def admin_env(db_session: AsyncSession) -> dict[str, Any]:
    network_a = Network(slug="net-a", name="Сеть A")
    network_b = Network(slug="net-b", name="Сеть B")
    db_session.add_all([network_a, network_b])
    await db_session.flush()

    branch_a = Branch(network_id=network_a.id, name="Филиал A1")
    branch_b = Branch(network_id=network_b.id, name="Филиал B1")
    db_session.add_all([branch_a, branch_b])
    await db_session.flush()

    avela = User(telegram_id=1, role=ROLE_AVELA_ADMIN)
    net_admin = User(telegram_id=2, role=ROLE_NETWORK_ADMIN, network_id=network_a.id)
    br_admin = User(telegram_id=3, role=ROLE_BRANCH_ADMIN)
    patient = User(telegram_id=4, role=ROLE_PATIENT, first_name="Пациент")
    db_session.add_all([avela, net_admin, br_admin, patient])
    await db_session.flush()

    db_session.add(BranchAdmin(user_id=br_admin.id, branch_id=branch_a.id))
    await db_session.commit()

    return {
        "network_a": network_a,
        "network_b": network_b,
        "branch_a": branch_a,
        "branch_b": branch_b,
        "avela": avela,
        "net_admin": net_admin,
        "br_admin": br_admin,
        "patient": patient,
    }


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession) -> httpx.AsyncClient:
    monkeypatch.setenv("BOT_TOKEN", "123456:test-token")
    monkeypatch.setenv("JWT_SECRET", SECRET)

    application = FastAPI()
    application.include_router(admin_catalog_router)
    application.include_router(admin_appointments_router)

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    application.dependency_overrides[get_session] = override_session
    transport = httpx.ASGITransport(app=application)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


def _headers(user: User) -> dict[str, str]:
    token = create_session_token(user.id, user.telegram_id, user.role, SECRET, ttl_seconds=3600)
    return {"Authorization": f"Bearer {token}"}


async def test_patient_forbidden(client: httpx.AsyncClient, admin_env: dict[str, Any]) -> None:
    response = await client.get("/admin/networks", headers=_headers(admin_env["patient"]))

    assert response.status_code == 403


async def test_network_admin_sees_only_own_network(
    client: httpx.AsyncClient, admin_env: dict[str, Any]
) -> None:
    response = await client.get("/admin/networks", headers=_headers(admin_env["net_admin"]))

    assert response.status_code == 200
    assert {row["id"] for row in response.json()} == {str(admin_env["network_a"].id)}


async def test_avela_admin_sees_all_networks(
    client: httpx.AsyncClient, admin_env: dict[str, Any]
) -> None:
    response = await client.get("/admin/networks", headers=_headers(admin_env["avela"]))

    assert response.status_code == 200
    assert len(response.json()) >= 2


async def test_network_admin_creates_branch_in_own_network(
    client: httpx.AsyncClient, admin_env: dict[str, Any]
) -> None:
    response = await client.post(
        f"/admin/networks/{admin_env['network_a'].id}/branches",
        json={"name": "Новый филиал", "city": "Минск", "timezone": "Europe/Minsk"},
        headers=_headers(admin_env["net_admin"]),
    )

    assert response.status_code == 201
    assert response.json()["timezone"] == "Europe/Minsk"


async def test_network_admin_cannot_create_branch_in_foreign_network(
    client: httpx.AsyncClient, admin_env: dict[str, Any]
) -> None:
    response = await client.post(
        f"/admin/networks/{admin_env['network_b'].id}/branches",
        json={"name": "Чужой филиал"},
        headers=_headers(admin_env["net_admin"]),
    )

    assert response.status_code == 404


async def test_invalid_timezone_rejected(
    client: httpx.AsyncClient, admin_env: dict[str, Any]
) -> None:
    response = await client.post(
        f"/admin/networks/{admin_env['network_a'].id}/branches",
        json={"name": "Кривой филиал", "timezone": "Марс/Олимп"},
        headers=_headers(admin_env["net_admin"]),
    )

    assert response.status_code == 422


async def test_branch_admin_sees_only_own_branches(
    client: httpx.AsyncClient, admin_env: dict[str, Any]
) -> None:
    response = await client.get("/admin/branches", headers=_headers(admin_env["br_admin"]))

    assert response.status_code == 200
    assert {row["id"] for row in response.json()} == {str(admin_env["branch_a"].id)}


async def test_branch_admin_cannot_update_foreign_branch(
    client: httpx.AsyncClient, admin_env: dict[str, Any]
) -> None:
    response = await client.patch(
        f"/admin/branches/{admin_env['branch_b'].id}",
        json={"phone": "+375 00 000-00-00"},
        headers=_headers(admin_env["br_admin"]),
    )

    assert response.status_code == 404


async def test_branch_admin_cannot_change_timezone(
    client: httpx.AsyncClient, admin_env: dict[str, Any]
) -> None:
    response = await client.patch(
        f"/admin/branches/{admin_env['branch_a'].id}",
        json={"timezone": "Asia/Tokyo"},
        headers=_headers(admin_env["br_admin"]),
    )

    assert response.status_code == 403


async def test_service_doctor_template_and_slots_flow(
    client: httpx.AsyncClient, admin_env: dict[str, Any]
) -> None:
    headers = _headers(admin_env["net_admin"])
    network_id = admin_env["network_a"].id
    branch_id = admin_env["branch_a"].id

    service_response = await client.post(
        f"/admin/networks/{network_id}/services",
        json={"name": "Терапия", "duration_minutes": 30},
        headers=headers,
    )
    assert service_response.status_code == 201
    service_id = service_response.json()["id"]

    doctor_response = await client.post(
        f"/admin/branches/{branch_id}/doctors",
        json={"full_name": "Иванов И.И.", "specialty": "Терапевт", "service_ids": [service_id]},
        headers=headers,
    )
    assert doctor_response.status_code == 201
    doctor_id = doctor_response.json()["id"]

    target = date.today() + timedelta(days=7)
    template_response = await client.post(
        f"/admin/doctors/{doctor_id}/schedule-templates",
        json={
            "service_id": service_id,
            "weekday": target.weekday(),
            "start_time": "09:00:00",
            "end_time": "10:00:00",
            "valid_from": target.isoformat(),
        },
        headers=headers,
    )
    assert template_response.status_code == 201
    template_id = template_response.json()["id"]

    generation = {"from_date": target.isoformat(), "to_date": target.isoformat()}
    first = await client.post(
        f"/admin/schedule-templates/{template_id}/generate-slots",
        json=generation,
        headers=headers,
    )
    assert first.status_code == 200
    assert first.json() == {"created": 2, "skipped": 0}

    # Повторная генерация идемпотентна: пересечения пропускаются, а не падают.
    second = await client.post(
        f"/admin/schedule-templates/{template_id}/generate-slots",
        json=generation,
        headers=headers,
    )
    assert second.json() == {"created": 0, "skipped": 2}


async def test_network_admin_cannot_touch_foreign_service(
    client: httpx.AsyncClient, db_session: AsyncSession, admin_env: dict[str, Any]
) -> None:
    foreign_service = Service(
        network_id=admin_env["network_b"].id, name="Чужая услуга", duration_minutes=30
    )
    db_session.add(foreign_service)
    await db_session.commit()

    response = await client.patch(
        f"/admin/services/{foreign_service.id}",
        json={"name": "Переименовано"},
        headers=_headers(admin_env["net_admin"]),
    )

    assert response.status_code == 404


async def test_admin_can_cancel_appointment_without_deadline(
    client: httpx.AsyncClient, db_session: AsyncSession, admin_env: dict[str, Any]
) -> None:
    patient = admin_env["patient"]
    service = Service(
        network_id=admin_env["network_a"].id, name="Терапия", duration_minutes=30
    )
    doctor = Doctor(branch_id=admin_env["branch_a"].id, full_name="Петров П.П.")
    db_session.add_all([service, doctor])
    await db_session.flush()

    now = datetime.now(UTC).replace(microsecond=0)
    slot = Slot(
        doctor_id=doctor.id,
        service_id=service.id,
        starts_at=now + timedelta(hours=1),
        ends_at=now + timedelta(hours=1, minutes=30),
    )
    db_session.add(slot)
    await db_session.flush()

    appointment = await book_slot(db_session, patient, slot.id)

    response = await client.post(
        f"/admin/appointments/{appointment.id}/cancel",
        headers=_headers(admin_env["br_admin"]),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "cancelled"
    assert body["cancelled_by"] == "admin"
    assert body["patient_telegram_id"] == patient.telegram_id

    audits = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.action == "appointment.cancel")
        )
    ).scalars().all()
    assert len(audits) == 1
    assert audits[0].actor_user_id == admin_env["br_admin"].id


async def test_branch_admin_cannot_cancel_foreign_appointment(
    client: httpx.AsyncClient, db_session: AsyncSession, admin_env: dict[str, Any]
) -> None:
    patient = admin_env["patient"]
    service = Service(
        network_id=admin_env["network_b"].id, name="Услуга B", duration_minutes=30
    )
    doctor = Doctor(branch_id=admin_env["branch_b"].id, full_name="Сидоров С.С.")
    db_session.add_all([service, doctor])
    await db_session.flush()

    now = datetime.now(UTC).replace(microsecond=0)
    slot = Slot(
        doctor_id=doctor.id,
        service_id=service.id,
        starts_at=now + timedelta(hours=2),
        ends_at=now + timedelta(hours=2, minutes=30),
    )
    db_session.add(slot)
    await db_session.flush()

    appointment = await book_slot(db_session, patient, slot.id)

    response = await client.post(
        f"/admin/appointments/{appointment.id}/cancel",
        headers=_headers(admin_env["br_admin"]),
    )

    assert response.status_code == 404
