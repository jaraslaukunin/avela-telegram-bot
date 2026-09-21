from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from aiogram.utils.web_app import (
    WebAppInitData,
    check_webapp_signature,
    safe_parse_webapp_init_data,
)

DEFAULT_MAX_AGE_SECONDS = 24 * 60 * 60
FUTURE_TOLERANCE_SECONDS = 60


class InvalidInitDataError(ValueError):
    """initData не прошла проверку — причина в сообщении."""


@dataclass(frozen=True)
class TelegramUser:
    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None


def validate_init_data(
    init_data: str,
    bot_token: str,
    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
) -> TelegramUser:
    """Проверяет Telegram Mini App initData.

    Подпись проверяется по официальному алгоритму Telegram
    (HMAC-SHA256, constant-time сравнение) через aiogram. Дополнительно
    проверяются срок годности auth_date, запрет времени из будущего
    и обязательное наличие данных пользователя.
    """
    if not init_data:
        raise InvalidInitDataError("initData пустая")

    if not check_webapp_signature(bot_token, init_data):
        raise InvalidInitDataError("Неверная подпись initData")

    try:
        data: WebAppInitData = safe_parse_webapp_init_data(bot_token, init_data)
    except ValueError as exc:
        raise InvalidInitDataError(f"initData не разбирается: {exc}") from exc

    auth_date = data.auth_date
    if auth_date.tzinfo is None:
        auth_date = auth_date.replace(tzinfo=UTC)
    now = datetime.now(UTC)

    if auth_date > now + timedelta(seconds=FUTURE_TOLERANCE_SECONDS):
        raise InvalidInitDataError("auth_date в будущем")
    if (now - auth_date).total_seconds() > max_age_seconds:
        raise InvalidInitDataError("initData устарела")

    user = data.user
    if user is None:
        raise InvalidInitDataError("initData без данных пользователя")

    return TelegramUser(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        language_code=user.language_code,
    )
