import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.deps import get_current_user
from app.core.security.initdata import InvalidInitDataError, validate_init_data
from app.core.security.jwt import create_session_token
from app.db import get_session
from app.models.user import User
from app.schemas import TelegramLoginRequest, TelegramLoginResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


async def _upsert_patient(
    session: AsyncSession,
    telegram_id: int,
    first_name: str,
    username: str | None,
    language_code: str | None,
) -> User:
    """Находит или создаёт пациента по telegram_id. Устойчиво к гонке входа."""
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


@router.post("/telegram")
async def login_telegram(
    payload: TelegramLoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TelegramLoginResponse:
    """Вход через Telegram Mini App initData → короткоживущий токен Avela."""
    settings = get_settings()

    try:
        tg_user = validate_init_data(payload.init_data, settings.bot_token)
    except InvalidInitDataError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    user = await _upsert_patient(
        session,
        tg_user.id,
        tg_user.first_name,
        tg_user.username,
        tg_user.language_code,
    )

    token = create_session_token(
        user.id,
        user.telegram_id,
        user.role,
        settings.jwt_secret,
        settings.jwt_ttl_seconds,
    )
    logger.info("Вход пациента telegram_id=%s", user.telegram_id)
    return TelegramLoginResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me")
async def me(current: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current)
