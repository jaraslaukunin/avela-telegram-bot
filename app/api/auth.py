import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.deps import get_current_user
from app.core.rate_limit import RateLimiter
from app.core.security.initdata import InvalidInitDataError, validate_init_data
from app.core.security.jwt import create_session_token
from app.db import get_session
from app.models.user import User
from app.schemas import TelegramLoginRequest, TelegramLoginResponse, UserOut
from app.services.users import get_or_create_user

AuthRateLimit = RateLimiter(limit=10)

router = APIRouter(
    prefix="/auth", tags=["auth"], dependencies=[Depends(AuthRateLimit)]
)
logger = logging.getLogger(__name__)


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

    user = await get_or_create_user(
        session,
        tg_user.id,
        first_name=tg_user.first_name,
        username=tg_user.username,
        language_code=tg_user.language_code,
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
