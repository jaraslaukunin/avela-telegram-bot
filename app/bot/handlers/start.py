from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.bot.keyboards.main_menu import get_main_menu


router = Router(name=__name__)


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    first_name = message.from_user.first_name if message.from_user else "пользователь"

    await message.answer(
        text=(
            f"Здравствуйте, {first_name}! 👋\n\n"
            "Вы в Avela — сервисе записи на приём к врачу.\n\n"
            "Выберите действие в меню ниже."
        ),
        reply_markup=get_main_menu(),
    )