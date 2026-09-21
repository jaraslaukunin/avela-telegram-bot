from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

from app.config import get_settings


def get_main_menu() -> ReplyKeyboardMarkup:
    """Главное меню. Кнопка Mini App появляется, если задан MINI_APP_URL."""
    rows: list[list[KeyboardButton]] = [
        [KeyboardButton(text="🏥 Записаться на приём")],
        [
            KeyboardButton(text="📋 Мои записи"),
            KeyboardButton(text="👤 Профиль"),
        ],
    ]

    mini_app_url = get_settings().mini_app_url
    if mini_app_url.startswith("https://"):
        # Кнопка Mini App: Telegram открывает приложение и передаёт initData.
        rows.append([KeyboardButton(text="📱 Приложение", web_app=WebAppInfo(url=mini_app_url))])

    rows.append(
        [
            KeyboardButton(text="❌ Отменить действие"),
            KeyboardButton(text="ℹ️ Информация"),
        ]
    )

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )
