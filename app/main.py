import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.admin_appointments import router as admin_appointments_router
from app.api.admin_catalog import router as admin_catalog_router
from app.api.appointments import router as appointments_router
from app.api.auth import router as auth_router
from app.api.catalog import router as catalog_router
from app.api.health import router as health_router
from app.api.privacy import router as privacy_router
from app.bot.handlers.appointments import router as bot_appointments_router
from app.bot.handlers.booking import router as bot_booking_router
from app.bot.handlers.fallback import router as bot_fallback_router
from app.bot.handlers.profile import router as profile_router
from app.bot.handlers.start import router as start_router
from app.bot.webhook import WEBHOOK_PATH, build_webhook_router
from app.config import get_settings
from app.core.logging import configure_logging, request_id_var
from app.core.middleware import RequestIdMiddleware, SecurityHeadersMiddleware

configure_logging()
logger = logging.getLogger(__name__)

settings = get_settings()

bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

dispatcher = Dispatcher(storage=MemoryStorage())
dispatcher.include_router(start_router)
dispatcher.include_router(bot_booking_router)
dispatcher.include_router(bot_appointments_router)
dispatcher.include_router(profile_router)
dispatcher.include_router(bot_fallback_router)


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
        try:
            await poll_task
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.warning(
                "Polling оборван при остановке (нормально при аварийном завершении)",
                exc_info=True,
            )

    await bot.session.close()


def create_app() -> FastAPI:
    application = FastAPI(title="Avela", version="0.1.0", lifespan=lifespan)

    cors_origins = settings.cors_origin_list
    if cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        )

    application.add_middleware(RequestIdMiddleware)
    application.add_middleware(SecurityHeadersMiddleware)

    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(catalog_router)
    application.include_router(appointments_router)
    application.include_router(admin_catalog_router)
    application.include_router(admin_appointments_router)
    application.include_router(privacy_router)
    application.include_router(build_webhook_router(bot, dispatcher, settings))

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Необработанная ошибка на %s", request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Внутренняя ошибка сервиса",
                "request_id": request_id_var.get(),
            },
        )

    return application


app = create_app()


def main() -> None:
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_config=None,
    )


if __name__ == "__main__":
    main()
