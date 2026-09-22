import asyncio
import logging
from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_engine() -> AsyncEngine:
    """Ленивый движок БД.

    Настройки пула важны из-за расстояния до Supabase: холодное соединение
    (TCP + TLS + авторизация у пулера) стоит около секунды, поэтому пул
    держит соединения открытыми, а `pool_pre_ping` отсекает те, что пулер
    успел закрыть.
    """
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        pool_timeout=10,
    )


async def keep_database_warm(interval_seconds: float = 25.0) -> None:
    """Держит соединение с БД тёплым, чтобы не платить за рукопожатие.

    Пулер Supabase закрывает простаивающие соединения, и первый запрос
    после паузы снова платит за TCP + TLS + авторизацию. Дешёвый `select 1`
    раз в интервал не даёт пулу остыть.
    """
    engine = get_engine()
    while True:
        try:
            async with engine.connect() as connection:
                await connection.execute(text("select 1"))
        except Exception:
            logger.warning("Прогрев соединения с БД не удался", exc_info=True)
        await asyncio.sleep(interval_seconds)


async def get_session() -> AsyncIterator[AsyncSession]:
    factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with factory() as session:
        yield session


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Фабрика сессий для фоновых задач (worker) и хэндлеров бота."""
    return async_sessionmaker(get_engine(), expire_on_commit=False)
