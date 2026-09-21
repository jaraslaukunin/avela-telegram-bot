import hashlib
import hmac
import json
import time
from urllib.parse import quote

import pytest

from app.core.security.initdata import (
    DEFAULT_MAX_AGE_SECONDS,
    InvalidInitDataError,
    TelegramUser,
    validate_init_data,
)

BOT_TOKEN = "123456:test-token"
USER = {"id": 42, "first_name": "Тест", "username": "tester", "language_code": "ru"}


def _sign(decoded: dict[str, str], bot_token: str) -> str:
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(decoded.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    return hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()


def build_init_data(
    bot_token: str = BOT_TOKEN,
    auth_date: int | None = None,
    user: dict[str, object] | None = USER,
    **extra: str,
) -> str:
    """Собирает initData так же, как это делает Telegram: значения в строке
    URL-кодируются, а подпись считается по декодированным значениям."""
    decoded: dict[str, str] = {}
    if auth_date is not None:
        decoded["auth_date"] = str(auth_date)
    if user is not None:
        decoded["user"] = json.dumps(user)
    decoded.update(extra)

    encoded = {key: quote(value) for key, value in decoded.items()}
    encoded["hash"] = _sign(decoded, bot_token)
    return "&".join(f"{key}={value}" for key, value in encoded.items())


def test_valid_init_data_returns_user() -> None:
    user = validate_init_data(build_init_data(auth_date=int(time.time())), BOT_TOKEN)

    assert isinstance(user, TelegramUser)
    assert user.id == 42
    assert user.first_name == "Тест"
    assert user.username == "tester"
    assert user.language_code == "ru"


def test_wrong_token_rejected() -> None:
    init_data = build_init_data(auth_date=int(time.time()))

    with pytest.raises(InvalidInitDataError):
        validate_init_data(init_data, "999999:wrong-token")


def test_tampered_field_rejected() -> None:
    init_data = build_init_data(auth_date=int(time.time()))
    tampered = init_data.replace("auth_date=", "auth_date=1", 1)

    with pytest.raises(InvalidInitDataError):
        validate_init_data(tampered, BOT_TOKEN)


def test_missing_hash_rejected() -> None:
    init_data = build_init_data(auth_date=int(time.time()))
    without_hash = init_data.split("&hash=")[0]

    with pytest.raises(InvalidInitDataError):
        validate_init_data(without_hash, BOT_TOKEN)


def test_empty_init_data_rejected() -> None:
    with pytest.raises(InvalidInitDataError):
        validate_init_data("", BOT_TOKEN)


def test_missing_auth_date_rejected() -> None:
    with pytest.raises(InvalidInitDataError):
        validate_init_data(build_init_data(), BOT_TOKEN)


def test_stale_auth_date_rejected() -> None:
    stale = int(time.time()) - DEFAULT_MAX_AGE_SECONDS - 60

    with pytest.raises(InvalidInitDataError):
        validate_init_data(build_init_data(auth_date=stale), BOT_TOKEN)


def test_future_auth_date_rejected() -> None:
    future = int(time.time()) + 3600

    with pytest.raises(InvalidInitDataError):
        validate_init_data(build_init_data(auth_date=future), BOT_TOKEN)


def test_missing_user_rejected() -> None:
    init_data = build_init_data(auth_date=int(time.time()), user=None)

    with pytest.raises(InvalidInitDataError):
        validate_init_data(init_data, BOT_TOKEN)


def test_malformed_user_json_rejected() -> None:
    decoded = {"auth_date": str(int(time.time())), "user": "not-json"}
    encoded = {key: quote(value) for key, value in decoded.items()}
    encoded["hash"] = _sign(decoded, BOT_TOKEN)
    init_data = "&".join(f"{key}={value}" for key, value in encoded.items())

    with pytest.raises(InvalidInitDataError):
        validate_init_data(init_data, BOT_TOKEN)
