import uuid

import pytest

from app.core.security.jwt import (
    InvalidSessionError,
    Session,
    create_session_token,
    decode_session_token,
)

SECRET = "unit-test-secret-0123456789abcdef"


def test_roundtrip() -> None:
    user_id = uuid.uuid4()

    token = create_session_token(user_id, 42, "patient", SECRET, ttl_seconds=3600)
    session = decode_session_token(token, SECRET)

    assert isinstance(session, Session)
    assert session.user_id == user_id
    assert session.telegram_id == 42
    assert session.role == "patient"


def test_wrong_secret_rejected() -> None:
    token = create_session_token(uuid.uuid4(), 42, "patient", SECRET, ttl_seconds=3600)

    with pytest.raises(InvalidSessionError):
        decode_session_token(token, "another-secret-0123456789abcdef")


def test_expired_token_rejected() -> None:
    token = create_session_token(uuid.uuid4(), 42, "patient", SECRET, ttl_seconds=-10)

    with pytest.raises(InvalidSessionError):
        decode_session_token(token, SECRET)


def test_tampered_token_rejected() -> None:
    token = create_session_token(uuid.uuid4(), 42, "patient", SECRET, ttl_seconds=3600)
    tampered = token[:-4] + "abcd"

    with pytest.raises(InvalidSessionError):
        decode_session_token(tampered, SECRET)
