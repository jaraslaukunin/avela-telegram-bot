"""Один экземпляр Bot на процесс.

Нужен и API (сообщения администратора пациенту), и webhook-роуту, и worker'у.
Лениво создаётся при первом обращении — импорт не требует BOT_TOKEN.
"""
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import get_settings

_bot: Bot | None = None


def get_bot() -> Bot:
    global _bot
    if _bot is None:
        settings = get_settings()
        _bot = Bot(
            token=settings.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
    return _bot
