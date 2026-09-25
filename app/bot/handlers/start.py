from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy import select

from app.bot.keyboards.main_menu import get_main_menu, get_phone_request_menu
from app.db import get_session_factory
from app.models.user import User
from app.services.users import get_or_create_user

router = Router(name=__name__)


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    telegram_user = message.from_user
    if telegram_user is None:
        return

    session_factory = get_session_factory()

    async with session_factory() as session:
        user = await get_or_create_user(session, telegram_user.id)
        await session.commit()

    first_name = telegram_user.first_name or "друг"

    if not user.phone:
        await message.answer(
            text=(
                f"Здравствуйте, {first_name}! 👋\n\n"
                "Чтобы клиника могла связаться с вами по поводу записи, "
                "поделитесь номером телефона.\n\n"
                "Нажмите «📱 Поделиться номером». Telegram передаст номер "
                "только после вашего подтверждения."
            ),
            reply_markup=get_phone_request_menu(),
        )
        return

    await message.answer(
        text=(
            f"Здравствуйте, {first_name}! 👋\n\n"
            "Я — Avela, запись к врачу. Вся запись, переносы и отмены — "
            "в приложении: нажмите «📱 Открыть Avela».\n\n"
            "Сюда я пришлю талон и напоминания о приёмах."
        ),
        reply_markup=get_main_menu(),
    )


@router.message(F.contact)
async def handle_contact(message: Message) -> None:
    contact = message.contact
    telegram_user = message.from_user

    if contact is None or telegram_user is None:
        return

    if contact.user_id != telegram_user.id:
        await message.answer(
            "Пожалуйста, поделитесь своим номером через кнопку "
            "«📱 Поделиться номером».",
        )
        return

    session_factory = get_session_factory()

    async with session_factory() as session:
        user = (
            await session.execute(
                select(User).where(User.telegram_id == telegram_user.id)
            )
        ).scalar_one_or_none()

        if user is None:
            await message.answer(
                "Сначала отправьте /start, затем повторите отправку номера.",
            )
            return

        user.phone = contact.phone_number
        await session.commit()

    await message.answer(
        "Номер сохранён ✅\n\nТеперь можно открыть приложение и записаться.",
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