import pytest
from pydantic import ValidationError

from app.config import Settings, get_settings


def test_get_settings_reads_token_and_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BOT_TOKEN", "123456:test-token")

    settings = get_settings(_env_file=None)

    assert isinstance(settings, Settings)
    assert settings.bot_token == "123456:test-token"
    assert settings.webhook_mode is False
    assert settings.api_port == 8000


def test_get_settings_requires_bot_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BOT_TOKEN", "")

    with pytest.raises(ValidationError):
        get_settings(_env_file=None)


def test_webhook_mode_requires_secret_and_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BOT_TOKEN", "123456:test-token")
    monkeypatch.setenv("WEBHOOK_MODE", "true")

    with pytest.raises(ValidationError):
        get_settings(_env_file=None)


def test_webhook_mode_accepts_full_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BOT_TOKEN", "123456:test-token")
    monkeypatch.setenv("WEBHOOK_MODE", "true")
    monkeypatch.setenv("WEBHOOK_SECRET", "very-secret")
    monkeypatch.setenv("WEBHOOK_BASE_URL", "https://bot.example.com")

    settings = get_settings(_env_file=None)

    assert settings.webhook_secret == "very-secret"
    assert settings.webhook_base_url == "https://bot.example.com"
