"""Точка входа worker'а: singleton-процесс с планировщиком.

Запуск: `python -m app.worker.main`
"""
import asyncio
import logging
from datetime import UTC
from typing import cast

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import get_settings
from app.core.logging import configure_logging
from app.db import get_session_factory
from app.worker.notifier import (
    MessageSender,
    dispatch_pending_notifications,
    write_heartbeat,
)

logger = logging.getLogger(__name__)


async def run_once(bot: Bot) -> None:
    factory = get_session_factory()
    async with factory() as session:
        await write_heartbeat(session)
        result = await dispatch_pending_notifications(session, cast(MessageSender, bot))
    if result.sent or result.skipped or result.failed:
        logger.info(
            "Уведомления: отправлено=%s, пропущено=%s, ошибок=%s",
            result.sent,
            result.skipped,
            result.failed,
        )


async def main() -> None:
    configure_logging()
    settings = get_settings()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    scheduler = AsyncIOScheduler(timezone=UTC)
    scheduler.add_job(
        run_once,
        "interval",
        seconds=settings.notifier_interval_seconds,
        args=[bot],
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info("Worker запущен, интервал=%s с", settings.notifier_interval_seconds)

    try:
        await run_once(bot)
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Worker останавливается")
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
