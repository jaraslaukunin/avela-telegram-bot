import time
from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import router as auth_router
from app.db import get_session
from tests.test_initdata import build_init_data


@pytest.fixture
async def client(
    monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession
) -> AsyncIterator[httpx.AsyncClient]:
    monkeypatch.setenv("BOT_TOKEN", "123456:test-token")
    monkeypatch.setenv("JWT_SECRET", "integration-test-secret-0123456789")

    application = FastAPI()
    application.include_router(auth_router)

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    application.dependency_overrides[get_session] = override_session
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def test_login_creates_patient_and_me_works(client: httpx.AsyncClient) -> None:
    init_data = build_init_data(auth_date=int(time.time()))

    response = await client.post("/auth/telegram", json={"init_data": init_data})

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["user"]["telegram_id"] == 42
    assert body["user"]["role"] == "patient"

    token = body["access_token"]
    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["telegram_id"] == 42


async def test_me_requires_token(client: httpx.AsyncClient) -> None:
    response = await client.get("/auth/me")

    assert response.status_code == 401


async def test_login_with_bad_init_data_rejected(client: httpx.AsyncClient) -> None:
    response = await client.post("/auth/telegram", json={"init_data": "hash=deadbeef"})

    assert response.status_code == 400


async def test_me_with_garbage_token_rejected(client: httpx.AsyncClient) -> None:
    response = await client.get(
        "/auth/me", headers={"Authorization": "Bearer definitely-not-a-token"}
    )

    assert response.status_code == 401
