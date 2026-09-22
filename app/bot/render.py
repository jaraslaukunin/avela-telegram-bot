"""Картинка-талончик записи.

Рисуем сами (Pillow), без внешних сервисов: в талончике — логотип-марка
в геометрии logo.svg, время приёма, услуга, врач, адрес и цена.

Шрифт: DejaVu из системы (в Docker он ставится пакетом fonts-dejavu-core).
Если шрифта нет — падаем на встроенный: текст будет простым, но картинка
всё равно отрисуется и не сломает запись.
"""
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH = 900
HEIGHT = 620

IVORY = (250, 247, 240)
CARD = (255, 255, 255)
BLUE = (15, 107, 245)
TEXT = (28, 28, 30)
MUTED = (107, 114, 128)

FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
)


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _logo_mark(draw: ImageDraw.ImageDraw, left: int, top: int, size: int) -> None:
    """Две точки и диагональ — как в logo.svg, только векторно и маленьким."""
    radius = int(size * 0.13)
    offset = int(size * 0.2)
    width = max(3, int(size * 0.18))

    x1, y1 = left + offset, top + size - offset
    x2, y2 = left + size - offset, top + offset

    draw.line((x1, y1, x2, y2), fill=BLUE, width=width)
    for x, y in ((x1, y1), (x2, y2)):
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=BLUE)


def _line(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, int, int] = TEXT,
) -> None:
    draw.text(xy, text, font=font, fill=fill)


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
    """Возвращает PNG-талончик записи."""
    image = Image.new("RGB", (WIDTH, HEIGHT), IVORY)
    draw = ImageDraw.Draw(image)

    margin = 24
    draw.rounded_rectangle(
        (margin, margin, WIDTH - margin, HEIGHT - margin),
        radius=28,
        fill=CARD,
    )

    title_font = _font(40)
    label_font = _font(24)
    value_font = _font(30)
    time_font = _font(52)
    small_font = _font(20)

    # Шапка: марка + название
    _logo_mark(draw, margin + 32, margin + 28, 52)
    _line(draw, (margin + 100, margin + 30), "Avela", title_font, BLUE)
    _line(
        draw,
        (margin + 103, margin + 78),
        "Талон предварительной записи",
        small_font,
        MUTED,
    )

    draw.line((margin + 32, margin + 132, WIDTH - margin - 32, margin + 132), fill=(232, 232, 232))

    # Время приёма — самое важное
    _line(draw, (margin + 32, margin + 156), when, time_font)
    _line(draw, (margin + 32, margin + 224), "время клиники", small_font, MUTED)

    rows = (
        ("Услуга", service),
        ("Врач", doctor),
        ("Адрес", f"{branch}, {address}" if address else branch),
        ("Цена", price),
    )

    y = margin + 272
    for label, value in rows:
        _line(draw, (margin + 32, y), label, label_font, MUTED)
        _line(draw, (margin + 32, y + 30), value[:52], value_font)
        y += 76

    footer_y = HEIGHT - margin - 58
    draw.line(
        (margin + 32, footer_y - 16, WIDTH - margin - 32, footer_y - 16),
        fill=(232, 232, 232),
    )
    _line(draw, (margin + 32, footer_y), f"Код записи: {code}", small_font, MUTED)
    _line(
        draw,
        (margin + 32, footer_y + 24),
        "Отмена и перенос — не позднее чем за 2 часа до приёма",
        small_font,
        MUTED,
    )

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
