"""Тесты талончика-картинки и форматирования цены (без Telegram и БД)."""
from decimal import Decimal
from io import BytesIO

from PIL import Image

from app.bot.formatting import format_price
from app.bot.render import HEIGHT, WIDTH, render_ticket


def _ticket(
    service: str = "Приём терапевта",
    doctor: str = "Иванов Иван Иванович",
    address: str = "ул. Примерная, 1",
) -> bytes:
    return render_ticket(
        when="25.09.2026 12:00",
        service=service,
        doctor=doctor,
        branch="Центральный филиал",
        address=address,
        price="120 р.",
        code="AB12CD34",
    )


def test_ticket_is_a_png() -> None:
    data = _ticket()

    assert data.startswith(b"\x89PNG")
    assert len(data) > 3000


def test_ticket_has_expected_size() -> None:
    image = Image.open(BytesIO(_ticket()))

    assert image.size == (WIDTH, HEIGHT)


def test_ticket_survives_long_text() -> None:
    data = _ticket(
        service="Очень длинное название услуги, которое не должно ломать картинку",
        doctor="Очень Длинное Имя Врача С Отчеством И Дополнительными Словами",
        address="улица Очень Длинная, дом 123, корпус 4, офис 56, этаж 7",
    )

    assert data.startswith(b"\x89PNG")


def test_format_price_without_trailing_zeros() -> None:
    assert format_price(Decimal("120.00")) == "120 р."
    assert format_price(Decimal("99.50")) == "99.50 р."
    assert format_price(None) == "не указана"
