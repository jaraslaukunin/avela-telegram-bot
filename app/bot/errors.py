"""Глобальный обработчик ошибок бота.

Пользователь никогда не должен остаться без ответа: ошибку логируем
полностью (в логах), а в чат уходит короткое человеческое сообщение.
"""
import logging

from aiogram.exceptions import TelegramAPIError
from aiogram.types import ErrorEvent

logger = logging.getLogger(__name__)


async def handle_bot_error(event: ErrorEvent) -> bool:
    error = event.exception

    # Ошибки самого Telegram API (недоступен, слишком длинное сообщение и т.п.)
    if isinstance(error, TelegramAPIError):
        logger.warning("Ошибка Telegram API: %s", error)
        return True

    logger.exception("Ошибка обработки update: %s", error)

    update = event.update
    try:
        if update.message is not None:
            await update.message.answer(
                "Произошла ошибка. Попробуйте ещё раз или чуть позже."
            )
        elif update.callback_query is not None:
            await update.callback_query.answer(
                "Произошла ошибка. Попробуйте ещё раз.", show_alert=True
            )
    except TelegramAPIError:
        pass

    return True
