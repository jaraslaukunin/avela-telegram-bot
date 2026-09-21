import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "")

TABLES = (
    "notifications",
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
