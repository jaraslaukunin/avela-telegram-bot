"""Тесты поиска для пациента: специалист → филиал → врач с ценой и временем."""
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.offers import router as offers_router
from app.core.security.jwt import create_session_token
from app.db import get_session
from app.models.catalog import Branch, Doctor, DoctorService, Network, Service
from app.models.schedule import Slot
from app.models.user import User

SECRET = "integration-test-secret-0123456789"


@pytest.fixture
def offers_client(
    monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession
) -> httpx.AsyncClient:
    monkeypatch.setenv("BOT_TOKEN", "123456:test-token")
    monkeypatch.setenv("JWT_SECRET", SECRET)

    application = FastAPI()
    application.include_router(offers_router)

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    application.dependency_overrides[get_session] = override_session
    transport = httpx.ASGITransport(app=application)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


def _headers(user: User) -> dict[str, str]:
    token = create_session_token(user.id, user.telegram_id, user.role, SECRET, 3600)
    return {"Authorization": f"Bearer {token}"}


async def _seed_two_cities(db_session: AsyncSession) -> dict[str, Any]:
    """Две сети в разных городах, один специалист, две цены, свободные слоты."""
    network_a = Network(slug="a", name="Сеть A")
    network_b = Network(slug="b", name="Сеть B")
    db_session.add_all([network_a, network_b])
    await db_session.flush()

    minsk = Branch(
        network_id=network_a.id,
        name="Филал в Минске",
        city="Минск",
        address="ул. Минская, 1",
        phone="+375 17 111-11-11",
        latitude=53.9006,
        longitude=27.5590,
    )
    gomel = Branch(
        network_id=network_b.id,
        name="Филиал в Гомеле",
        city="Гомель",
        address="ул. Гомельская, 2",
        phone="+375 23 222-22-22",
        latitude=52.4345,
        longitude=30.9754,
    )
    db_session.add_all([minsk, gomel])
    await db_session.flush()

    service_a = Service(
        network_id=network_a.id, name="Терапевт", duration_minutes=30
    )
    service_b = Service(
        network_id=network_b.id, name="Терапевт", duration_minutes=30
    )
    user = User(telegram_id=777, first_name="Тест", role="patient")
    doctor_minsk = Doctor(branch_id=minsk.id, full_name="Минский Врач", specialty="Терапевт")
    doctor_gomel = Doctor(branch_id=gomel.id, full_name="Гомельский Врач", specialty="Терапевт")
    db_session.add_all([service_a, service_b, user, doctor_minsk, doctor_gomel])
    await db_session.flush()

    db_session.add_all(
        [
            DoctorService(
                doctor_id=doctor_minsk.id,
                service_id=service_a.id,
                price=Decimal("120.00"),
            ),
            DoctorService(
                doctor_id=doctor_gomel.id,
                service_id=service_b.id,
                price=Decimal("90.00"),
            ),
        ]
    )

    now = datetime.now(UTC).replace(microsecond=0)

    def slot(doctor: Doctor, service: Service, hours: int) -> Slot:
        return Slot(
            doctor_id=doctor.id,
            service_id=service.id,
            starts_at=now + timedelta(hours=hours),
            ends_at=now + timedelta(hours=hours, minutes=30),
            price=Decimal("120.00") if doctor is doctor_minsk else Decimal("90.00"),
        )

    db_session.add_all(
        [
            slot(doctor_minsk, service_a, 3),
            slot(doctor_minsk, service_a, 27),
            slot(doctor_gomel, service_b, 5),
        ]
    )
    await db_session.commit()

    return {
        "user": user,
        "minsk": minsk,
        "gomel": gomel,
        "doctor_minsk": doctor_minsk,
        "service_a": service_a,
    }


async def test_services_are_deduplicated_by_name(
    offers_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    ids = await _seed_two_cities(db_session)

    response = await offers_client.get("/catalog/services", headers=_headers(ids["user"]))

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "Терапевт"
    assert body[0]["networks_count"] == 2


async def test_cities_list(
    offers_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    ids = await _seed_two_cities(db_session)

    response = await offers_client.get("/catalog/cities", headers=_headers(ids["user"]))

    assert response.status_code == 200
    assert response.json() == ["Гомель", "Минск"]


async def test_offers_have_price_and_next_slot(
    offers_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    ids = await _seed_two_cities(db_session)

    response = await offers_client.get(
        "/catalog/offers", params={"service_name": "Терапевт"}, headers=_headers(ids["user"])
    )

    assert response.status_code == 200
    offers = response.json()["offers"]
    assert len(offers) == 2

    # Ближайшее время выше: у минского врача слот через 3 часа, у гомельского — через 5.
    assert offers[0]["doctor_name"] == "Минский Врач"
    assert offers[0]["price"] == "120.00"
    assert offers[0]["slots_count"] == 2
    assert offers[0]["city"] == "Минск"
    assert offers[1]["doctor_name"] == "Гомельский Врач"
    assert offers[1]["price"] == "90.00"
    # service_id нужен клиенту, чтобы открыть слоты конкретного врача.
    assert offers[0]["service_id"] == str(ids["service_a"].id)


async def test_offers_can_be_filtered_by_city(
    offers_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    ids = await _seed_two_cities(db_session)

    response = await offers_client.get(
        "/catalog/offers",
        params={"service_name": "Терапевт", "city": "Гомель"},
        headers=_headers(ids["user"]),
    )

    offers = response.json()["offers"]
    assert len(offers) == 1
    assert offers[0]["city"] == "Гомель"


async def test_offers_sorted_by_distance_from_patient(
    offers_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    ids = await _seed_two_cities(db_session)

    # Координаты — Минск: минский филиал должен быть первым и с расстоянием.
    response = await offers_client.get(
        "/catalog/offers",
        params={"service_name": "Терапевт", "latitude": 53.9, "longitude": 27.56},
        headers=_headers(ids["user"]),
    )

    offers = response.json()["offers"]
    assert offers[0]["city"] == "Минск"
    assert offers[0]["distance_km"] is not None
    assert offers[0]["distance_km"] < 5
    assert offers[1]["distance_km"] > 200


async def test_offers_require_authorization(
    offers_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await _seed_two_cities(db_session)

    response = await offers_client.get(
        "/catalog/offers", params={"service_name": "Терапевт"}
    )

    assert response.status_code == 401
