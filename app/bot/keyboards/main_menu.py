from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🏥 Записаться на приём"),
            ],
            [
                KeyboardButton(text="📋 Мои записи"),
                KeyboardButton(text="👤 Профиль"),
            ],
            [
                KeyboardButton(text="❌ Отменить действие"),
                KeyboardButton(text="ℹ️ Информация"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )
