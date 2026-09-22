from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

from app.config import get_settings


def get_main_menu() -> ReplyKeyboardMarkup:
    """Минимальное меню: вся запись — в Mini App.

    Если MINI_APP_URL не задан, остаётся только информационная кнопка.
    """
    rows: list[list[KeyboardButton]] = []

    mini_app_url = get_settings().mini_app_url
    if mini_app_url.startswith("https://"):
        rows.append(
            [KeyboardButton(text="📱 Открыть Avela", web_app=WebAppInfo(url=mini_app_url))]
        )

    rows.append([KeyboardButton(text="ℹ️ Информация")])

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder="Запись — в приложении",
    )
