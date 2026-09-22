"""Общие помощники хэндлеров бота: пользователь, слоты, callback-данные."""
import logging
import uuid
from datetime import UTC, datetime, timedelta

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.bot.formatting import slot_button_label
from app.db import get_session_factory
from app.models.schedule import Slot
from app.models.user import User
from app.services.booking import list_available_slots
from app.services.users import get_or_create_user

logger = logging.getLogger(__name__)

SLOTS_WINDOW_DAYS = 14
MAX_SLOT_BUTTONS = 12


async def get_bot_user(source: Message | CallbackQuery) -> User | None:
    """Находит (или создаёт) пользователя БД по данным Telegram update.

    telegram_id из update аутентичен: его присылает сам Telegram.
    Если БД недоступна — пользователь получает понятное сообщение,
    а не молчание.
    """
    telegram_user = source.from_user
    if telegram_user is None:
        if isinstance(source, CallbackQuery):
            await source.answer(
                "Не удалось определить ваш аккаунт Telegram. Попробуйте ещё раз.",
                show_alert=True,
            )
        else:
            await source.answer(
                "Не удалось определить ваш аккаунт Telegram. Попробуйте ещё раз."
            )
        return None

    factory = get_session_factory()
    try:
        async with factory() as session:
            return await get_or_create_user(
                session,
                telegram_id=telegram_user.id,
                first_name=telegram_user.first_name,
                username=telegram_user.username,
                language_code=telegram_user.language_code,
            )
    except Exception:
        logger.exception("Не удалось получить пользователя из БД")
        text = "База данных временно недоступна — попробуйте позже."
        if isinstance(source, CallbackQuery):
            await source.answer(text, show_alert=True)
        else:
            await source.answer(text)
        return None


async def show_step(
    callback: CallbackQuery,
    text: str,
    keyboard: InlineKeyboardMarkup | None = None,
) -> None:
    """Показывает следующий шаг В ОДНОМ сообщении, а не новым.

    Чат не засоряется: шаг записи правит предыдущий. Если Telegram не даёт
    править (сообщение слишком старое, это фото, либо текст не изменился) —
    отправляем новое сообщение, чтобы пользователь точно увидел ответ.
    """
    message = callback.message
    if isinstance(message, Message):
        try:
            await message.edit_text(text, reply_markup=keyboard)
            return
        except TelegramBadRequest:
            await message.answer(text, reply_markup=keyboard)
            return

    # Сообщение недоступно для правки (слишком старое) — отправляем новое.
    if message is not None and callback.bot is not None:
        await callback.bot.send_message(message.chat.id, text, reply_markup=keyboard)


def parse_uuid(data: str, prefix: str) -> uuid.UUID | None:
    """Разбирает uuid из callback_data («net:...», «slot:...» и т.п.)."""
    try:
        return uuid.UUID(data.removeprefix(prefix))
    except ValueError:
        return None


def build_slots_keyboard(slots: list[Slot], timezone_name: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=slot_button_label(slot, timezone_name),
                    callback_data=f"slot:{slot.id}",
                )
            ]
            for slot in slots
        ]
    )


async def fetch_free_slots(
    service_id: uuid.UUID,
    branch_id: uuid.UUID | None = None,
    doctor_id: uuid.UUID | None = None,
) -> tuple[list[Slot], str]:
    """Свободные слоты на ближайшие две недели + таймзона для отображения.

    Таймзону берём из филиала: если слотов нет и филиал не задан,
    отображение не важно — возвращаем UTC.
    """
    now = datetime.now(UTC)
    factory = get_session_factory()
    async with factory() as session:
        rows = await list_available_slots(
            session,
            service_id,
            from_dt=now,
            to_dt=now + timedelta(days=SLOTS_WINDOW_DAYS),
            branch_id=branch_id,
            doctor_id=doctor_id,
        )
        slots = [slot for slot, _doctor, _branch in rows]
        timezone_name = "UTC"
        if rows:
            timezone_name = rows[0][2].timezone
        return slots[:MAX_SLOT_BUTTONS], timezone_name
