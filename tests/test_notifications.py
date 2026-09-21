"""Тесты текстов уведомлений (без БД и Telegram)."""
from datetime import UTC, datetime

from app.services.notifications import (
    BOOKING_CREATED,
    CANCELLED,
    REMINDER_2H,
    REMINDER_24H,
    RESCHEDULED,
    format_local_time,
    render_message,
)

STARTS_AT = datetime(2026, 9, 25, 12, 0, tzinfo=UTC)  # 15:00 в Москве


def _render(kind: str) -> str:
    return render_message(
        kind,
        doctor_name="Иванов И.И.",
        service_name="Приём терапевта",
        branch_name="Филиал на Ленина",
        branch_address="ул. Ленина, 1",
        branch_phone="+375 17 000-00-00",
        starts_at=STARTS_AT,
        timezone_name="Europe/Moscow",
    )


def test_local_time_uses_branch_timezone() -> None:
    assert format_local_time(STARTS_AT, "Europe/Moscow") == "25.09.2026 15:00"
    assert format_local_time(STARTS_AT, "Europe/Minsk") == "25.09.2026 15:00"


def test_invalid_timezone_falls_back_to_utc() -> None:
    assert format_local_time(STARTS_AT, "Марс/Олимп") == "25.09.2026 12:00"


def test_every_kind_contains_appointment_facts() -> None:
    for kind in (BOOKING_CREATED, REMINDER_24H, REMINDER_2H, CANCELLED, RESCHEDULED):
        text = _render(kind)
        assert "Приём терапевта" in text
        assert "Иванов И.И." in text
        assert "25.09.2026 15:00" in text


def test_reminder_texts_are_distinguishable() -> None:
    assert "приём завтра" in _render(REMINDER_24H)
    assert "через 2 часа" in _render(REMINDER_2H)


def test_cancelled_message_has_clinic_phone() -> None:
    assert "+375 17 000-00-00" in _render(CANCELLED)


def test_unknown_kind_still_renders_appointment_facts() -> None:
    assert "Приём терапевта" in _render("unknown_kind")
