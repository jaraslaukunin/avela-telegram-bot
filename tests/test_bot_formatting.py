"""Тесты форматирования сообщений бота (без БД)."""
import uuid
from datetime import UTC, datetime, timedelta

from app.bot.formatting import (
    format_appointment_card,
    format_booked_message,
    format_rescheduled_message,
    slot_button_label,
)
from app.models.catalog import Branch, Doctor, Service
from app.models.schedule import Slot

STARTS = datetime(2026, 9, 25, 9, 0, tzinfo=UTC)  # 12:00 в Минске (UTC+3)


def _slot() -> Slot:
    return Slot(
        doctor_id=uuid.uuid4(),
        service_id=uuid.uuid4(),
        starts_at=STARTS,
        ends_at=STARTS + timedelta(minutes=30),
    )


def _doctor() -> Doctor:
    return Doctor(
        branch_id=uuid.uuid4(),
        full_name="Иванов Иван Иванович",
        specialty="Терапевт",
    )


def _service() -> Service:
    return Service(
        network_id=uuid.uuid4(), name="Приём терапевта", duration_minutes=30
    )


def _branch() -> Branch:
    return Branch(
        network_id=uuid.uuid4(),
        name="Центральный филиал",
        address="ул. Примерная, 1",
        phone="+375 17 000-00-00",
        timezone="Europe/Minsk",
    )


def test_slot_button_label_uses_clinic_timezone() -> None:
    assert slot_button_label(_slot(), "Europe/Minsk") == "25.09 12:00"


def test_slot_button_label_falls_back_on_bad_timezone() -> None:
    assert slot_button_label(_slot(), "Марс/Олимп") == "25.09 09:00"


def test_booked_message_has_all_facts() -> None:
    text = format_booked_message(_slot(), _doctor(), _service(), _branch())

    assert "Приём терапевта" in text
    assert "Иванов Иван Иванович" in text
    assert "25.09.2026 12:00" in text
    assert "за 2 часа" in text


def test_appointment_card_has_address_and_phone() -> None:
    text = format_appointment_card(_slot(), _doctor(), _service(), _branch())

    assert "ул. Примерная, 1" in text
    assert "+375 17 000-00-00" in text


def test_rescheduled_message_differs_from_booked() -> None:
    text = format_rescheduled_message(_slot(), _doctor(), _service(), _branch())

    assert "перенесена" in text
