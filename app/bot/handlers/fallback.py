"""Финальный рубеж: на любое сообщение ведём в Mini App.

Бот не ведёт диалог о записи — только уведомления. Регистрируется
последним, чтобы ловить всё нераспознанное.
"""
from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.main_menu import get_main_menu

router = Router(name=__name__)


@router.message(F.text)
async def unhandled_text(message: Message) -> None:
    await message.answer(
        "Я не отвечаю в чате — запись, перенос и отмена живут в приложении.\n"
        "Нажмите «📱 Открыть Avela».",
        reply_markup=get_main_menu(),
    )


@router.callback_query()
async def unhandled_callback(callback: CallbackQuery) -> None:
    await callback.answer("Откройте приложение — там всё.")
