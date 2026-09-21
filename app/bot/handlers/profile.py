from aiogram import F, Router
from aiogram.types import Message

from app.bot.keyboards.main_menu import get_main_menu
from app.bot.keyboards.profile import get_profile_menu
from app.storage.profiles import UserProfile, profiles

router = Router(name=__name__)


def get_or_create_profile(message: Message) -> UserProfile:
    user = message.from_user

    if user is None:
        raise ValueError("Не удалось получить данные пользователя Telegram.")

    profile = profiles.get(user.id)

    if profile is None:
        profile = UserProfile(
            telegram_id=user.id,
            full_name=user.full_name,
            username=user.username,
        )
        profiles[user.id] = profile
    else:
        profile.full_name = user.full_name
        profile.username = user.username

    return profile


def format_profile(profile: UserProfile) -> str:
    username = f"@{profile.username}" if profile.username else "не указан"
    phone = profile.phone or "не указан"

    return (
        "👤 <b>Ваш профиль</b>\n\n"
        f"Имя: {profile.full_name}\n"
        f"Username: {username}\n"
        f"Телефон: {phone}\n\n"
        "Номер телефона нужен, чтобы клиника могла связаться с вами "
        "для подтверждения или уточнения записи."
    )


@router.message(F.text == "👤 Профиль")
async def show_profile(message: Message) -> None:
    profile = get_or_create_profile(message)

    await message.answer(
        text=format_profile(profile),
        reply_markup=get_profile_menu(has_phone=profile.phone is not None),
    )


@router.message(F.contact)
async def save_phone(message: Message) -> None:
    user = message.from_user
    contact = message.contact

    if user is None or contact is None:
        return

    if contact.user_id != user.id:
        await message.answer(
            "Пожалуйста, передайте свой номер через кнопку "
            "«📱 Поделиться номером».",
        )
        return

    profile = get_or_create_profile(message)
    profile.phone = contact.phone_number

    await message.answer(
        text=(
            "✅ <b>Номер телефона сохранён</b>\n\n"
            "Теперь вы сможете оформлять записи на приём."
        ),
        reply_markup=get_profile_menu(has_phone=True),
    )

    await message.answer(
        text=format_profile(profile),
        reply_markup=get_profile_menu(has_phone=True),
    )


@router.message(F.text == "🏠 Главное меню")
async def return_to_main_menu(message: Message) -> None:
    await message.answer(
        "Главное меню",
        reply_markup=get_main_menu(),
    )