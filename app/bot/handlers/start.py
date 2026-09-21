from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.helpers import get_bot_user
from app.bot.keyboards.main_menu import get_main_menu

router = Router(name=__name__)


@router.message(CommandStart())
async def handle_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await get_bot_user(message)  # регистрирует пользователя в БД, если его ещё нет

    first_name = message.from_user.first_name if message.from_user else "друг"
    await message.answer(
        text=(
            f"Здравствуйте, {first_name}! 👋\n\n"
            "Я Avela — запись на приём к врачу.\n\n"
            "Нажмите «🏥 Записаться на приём»: выберите клинику, услугу, "
            "филиал, врача и удобное время — остальное я возьму на себя."
        ),
        reply_markup=get_main_menu(),
    )


@router.message(F.text == "ℹ️ Информация")
async def show_info(message: Message) -> None:
    await message.answer(
        "ℹ️ <b>Об Avela</b>\n\n"
        "Предварительная запись на приём к врачу.\n"
        "Отменить или перенести запись можно не позднее чем за 2 часа до приёма.\n\n"
        "Бот не заменяет врача и не является медицинской консультацией.",
        reply_markup=get_main_menu(),
    )
