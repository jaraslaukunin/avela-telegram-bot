"""Пользователи: поиск или создание записи по telegram_id.

Один код для Mini App (после проверки initData) и для чата бота
(telegram_id берётся из самого update — он аутентичен).
"""
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    *,
    first_name: str = "",
    username: str | None = None,
    language_code: str | None = None,
) -> User:
    """Находит или создаёт пользователя. Устойчиво к гонке входа."""
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is None:
        user = User(telegram_id=telegram_id, role="patient")
        session.add(user)

    user.first_name = first_name
    user.username = username
    user.language_code = language_code

    try:
        await session.commit()
    except IntegrityError:
        # Гонка: два одновременных входа с одним telegram_id.
        # Уникальный индекс пропустил только одного — перечитываем победителя.
        await session.rollback()
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if user is None:
            raise
    return user
