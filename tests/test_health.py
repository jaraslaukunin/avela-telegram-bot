"""Тесты публичных health/ready/status (нужна Postgres)."""
from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.health import router as health_router
from app.db import get_session
from app.models.service import ServiceHeartbeat
from app.worker.notifier import write_heartbeat


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession) -> httpx.AsyncClient:
    monkeypatch.setenv("BOT_TOKEN", "123456:test-token")

    application = FastAPI()
    application.include_router(health_router)

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    application.dependency_overrides[get_session] = override_session
    transport = httpx.ASGITransport(app=application)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def test_health_is_public_and_minimal(client: httpx.AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_ready_reports_database(client: httpx.AsyncClient) -> None:
    response = await client.get("/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"]["database"] == "ok"


async def test_status_reports_components_without_secrets(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get("/status")

    assert response.status_code == 200
    body = response.json()
    assert body["components"]["api"] == "ok"
    assert body["components"]["database"] == "ok"
    assert body["components"]["worker"] == "not_started"

    # Никаких строк подключения, ключей и адресов.
    payload = response.text
    assert "postgres" not in payload
    assert "secret" not in payload.lower()


async def test_status_shows_worker_alive_after_heartbeat(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await write_heartbeat(db_session, "worker")

    heartbeat = await db_session.get(ServiceHeartbeat, "worker")
    assert heartbeat is not None

    response = await client.get("/status")
    assert response.json()["components"]["worker"] == "ok"
