from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.bot.keyboards.main_menu import get_main_menu

router = Router(name=__name__)


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    first_name = message.from_user.first_name if message.from_user else "друг"
    await message.answer(
        text=(
            f"Здравствуйте, {first_name}! 👋\n\n"
            "Я — Avela, запись к врачу. Вся запись, переносы и отмены — "
            "в приложении: нажмите «📱 Открыть Avela».\n\n"
            "Сюда я пришлю талон и напоминания о приёмах."
        ),
        reply_markup=get_main_menu(),
    )


@router.message(F.text == "ℹ️ Информация")
async def show_info(message: Message) -> None:
    await message.answer(
        "ℹ️ <b>Об Avela</b>\n\n"
        "Запись на приём к врачу: клиники, врачи, свободное время.\n"
        "Всё — в приложении по кнопке «📱 Открыть Avela».\n\n"
        "Бот не заменяет врача и не является медицинской консультацией.",
        reply_markup=get_main_menu(),
    )
