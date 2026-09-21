from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security.jwt import InvalidSessionError, decode_session_token
from app.db import get_session
from app.models.user import User


async def get_current_user(
    session: Annotated[AsyncSession, Depends(get_session)],
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """Текущий пользователь из Bearer-токена.

    Роль берётся из БД (свежая), а не из токена: заблокированный или
    удалённый пользователь сразу теряет доступ.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Требуется авторизация")

    token = authorization.removeprefix("Bearer ").strip()
    settings = get_settings()

    try:
        parsed = decode_session_token(token, settings.jwt_secret)
    except InvalidSessionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    user = await session.get(User, parsed.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Пользователь не найден или заблокирован")
    return user
