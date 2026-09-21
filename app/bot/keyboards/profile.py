from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_profile_menu(has_phone: bool) -> ReplyKeyboardMarkup:
    rows = []

    if not has_phone:
        rows.append(
            [
                KeyboardButton(
                    text="📱 Поделиться номером",
                    request_contact=True,
                ),
            ]
        )

    rows.append(
        [
            KeyboardButton(text="🏠 Главное меню"),
        ],
    )

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )