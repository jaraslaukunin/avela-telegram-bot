import time
import uuid
from dataclasses import dataclass

import jwt

ALGORITHM = "HS256"
ISSUER = "avela"


class InvalidSessionError(ValueError):
    """Токен не прошёл проверку — причина в сообщении."""


@dataclass(frozen=True)
class Session:
    user_id: uuid.UUID
    telegram_id: int
    role: str


def create_session_token(
    user_id: uuid.UUID,
    telegram_id: int,
    role: str,
    secret: str,
    ttl_seconds: int,
) -> str:
    """Короткоживущая сессия Avela после серверной проверки initData."""
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "telegram_id": telegram_id,
        "role": role,
        "iat": now,
        "exp": now + ttl_seconds,
        "iss": ISSUER,
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def decode_session_token(token: str, secret: str) -> Session:
    try:
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM], issuer=ISSUER)
    except jwt.PyJWTError as exc:
        raise InvalidSessionError("Сессия невалидна или истекла") from exc

    try:
        return Session(
            user_id=uuid.UUID(payload["sub"]),
            telegram_id=int(payload["telegram_id"]),
            role=str(payload["role"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidSessionError("Некорректные данные сессии") from exc
