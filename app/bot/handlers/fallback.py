"""Финальный рубеж: бот всегда отвечает, даже на нераспознанное.

Регистрируется последним — сюда попадают только сообщения и callback'и,
которые не обработал ни один бизнес-хэндлер.
"""
from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.main_menu import get_main_menu

router = Router(name=__name__)


@router.message(F.text)
async def unhandled_text(message: Message) -> None:
    await message.answer(
        "Я вас не понял 🤔\nВоспользуйтесь кнопками меню ниже.",
        reply_markup=get_main_menu(),
    )


@router.callback_query()
async def unhandled_callback(callback: CallbackQuery) -> None:
    await callback.answer("Это действие уже неактуально — начните заново из меню.")
