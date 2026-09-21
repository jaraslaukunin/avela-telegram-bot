from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.bot.keyboards.main_menu import get_main_menu
from app.storage.profiles import UserProfile, profiles

router = Router(name=__name__)


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    first_name = message.from_user.first_name if message.from_user else "пользователь"

    if message.from_user:
        profiles.setdefault(
            message.from_user.id,
            UserProfile(
                telegram_id=message.from_user.id,
                full_name=message.from_user.full_name,
                username=message.from_user.username,
            ),
        )

    await message.answer(
        text=(
            f"Здравствуйте, {first_name}! 👋\n\n"
            "Вы в Avela — сервисе записи на приём к врачу.\n\n"
            "Выберите действие в меню ниже."
        ),
        reply_markup=get_main_menu(),
    )