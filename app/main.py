import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from fastapi import FastAPI

from app.api.health import router as health_router
from app.bot.handlers.profile import router as profile_router
from app.bot.handlers.start import router as start_router
from app.bot.webhook import WEBHOOK_PATH, build_webhook_router
from app.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

settings = get_settings()

bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

dispatcher = Dispatcher()
dispatcher.include_router(start_router)
dispatcher.include_router(profile_router)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    poll_task: asyncio.Task[None] | None = None

    if settings.webhook_mode:
        await bot.set_webhook(
            url=f"{settings.webhook_base_url.rstrip('/')}{WEBHOOK_PATH}",
            secret_token=settings.webhook_secret,
        )
    else:
        await bot.delete_webhook(drop_pending_updates=True)
        poll_task = asyncio.create_task(dispatcher.start_polling(bot))

    yield

    if poll_task is not None:
        poll_task.cancel()
        with suppress(asyncio.CancelledError):
            await poll_task

    await bot.session.close()


def create_app() -> FastAPI:
    application = FastAPI(title="Avela", version="0.1.0", lifespan=lifespan)
    application.include_router(health_router)
    application.include_router(build_webhook_router(bot, dispatcher, settings))
    return application


app = create_app()


def main() -> None:
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)


if __name__ == "__main__":
    main()
