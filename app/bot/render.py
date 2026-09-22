"""Талон предварительной записи — PNG для Telegram.

Рисуем на Pillow: крупная дата и время, врач, услуга, филиал, адрес, цена.
Текст с переносами — ничего не накладывается при любых длинных значениях.
"""
import io
from typing import cast

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1080, 1440
IVORY = (250, 247, 240)
WHITE = (255, 255, 255)
BLUE = (15, 107, 245)
BLUE_SOFT = (222, 235, 255)
INK = (28, 28, 30)
MUTED = (118, 128, 140)
LINE = (222, 226, 236)

_font_cache: dict[tuple[bool, int], ImageFont.FreeTypeFont] = {}


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """DejaVu в Docker, Arial на macOS, встроенный шрифт как последний рубеж."""
    key = (bold, size)
    if key not in _font_cache:
        names = (
            "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
            "Arial Bold.ttf" if bold else "Arial.ttf",
        )
        prefixes = (
            "/usr/share/fonts/truetype/dejavu/",
            "/System/Library/Fonts/Supplemental/",
            "/Library/Fonts/",
            "",
        )
        font: ImageFont.FreeTypeFont | None = None
        for name in names:
            for prefix in prefixes:
                try:
                    font = ImageFont.truetype(prefix + name, size)
                    break
                except OSError:
                    continue
            if font is not None:
                break
        if font is None:
            font = cast(ImageFont.FreeTypeFont, ImageFont.load_default())
        _font_cache[key] = font
    return _font_cache[key]


def _draw_wrapped(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
    max_width: int,
) -> int:
    """Рисует текст с переносами по словам; возвращает y после последней строки."""
    x, y = xy
    words = (text or "—").split()
    line = ""
    line_height = int(getattr(font, "size", 20)) + 14

    for word in words:
        candidate = f"{line} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width:
            line = candidate
        else:
            if line:
                draw.text((x, y), line, font=font, fill=fill)
                y += line_height
            line = word

    if line:
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height
    return y


def render_ticket(
    *,
    when: str,
    service: str,
    doctor: str,
    branch: str,
    address: str,
    price: str,
    code: str,
) -> bytes:
    """Рисует PNG-талон. Чистая функция — тестируется без Telegram и БД."""
    image = Image.new("RGB", (WIDTH, HEIGHT), IVORY)
    draw = ImageDraw.Draw(image)

    # Шапка: логотип-плашка, название, подсказка.
    header_height = 320
    draw.rectangle([(0, 0), (WIDTH, header_height)], fill=BLUE)
    draw.rounded_rectangle(
        [(48, 52), (176, 180)], radius=24, fill=WHITE
    )
    draw.text((84, 78), "A", font=_font(64, bold=True), fill=BLUE)
    draw.text((208, 78), "Avela", font=_font(56, bold=True), fill=WHITE)
    draw.text((208, 156), "Талон предварительной записи", font=_font(34), fill=WHITE)
    draw.text(
        (48, 236),
        "Покажите его администратору на стойке",
        font=_font(28),
        fill=BLUE_SOFT,
    )

    left = 64
    right = WIDTH - 64
    y = header_height + 64

    # Дата и время — самое крупное на талоне.
    parts = when.split(" ", 1)
    date_text = parts[0] if parts else ""
    time_text = parts[1] if len(parts) > 1 else ""

    draw.text((left, y), date_text, font=_font(46, bold=True), fill=INK)
    y += 70
    draw.text((left, y), time_text, font=_font(104, bold=True), fill=BLUE)
    y += 156

    def divider(current_y: int) -> int:
        draw.line([(left, current_y), (right, current_y)], fill=LINE, width=4)
        return current_y + 52

    y = divider(y)

    rows = (
        ("Врач", doctor),
        ("Услуга", service),
        ("Филиал", branch),
        ("Адрес", address),
        ("Цена", price),
    )
    for label, value in rows:
        draw.text((left, y), label, font=_font(30), fill=MUTED)
        y += 48
        y = _draw_wrapped(draw, (left, y), value, _font(42, bold=True), INK, right - left)
        y += 44

    y = divider(y)

    draw.text((left, y), f"Номер записи: {code}", font=_font(32), fill=MUTED)
    y += 58
    draw.text((left, y), "Avela — запись к врачу", font=_font(28), fill=MUTED)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
