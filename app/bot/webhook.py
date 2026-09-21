import hmac
import logging
from typing import Annotated

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import Response

from app.config import Settings

logger = logging.getLogger(__name__)

WEBHOOK_PATH = "/telegram/webhook"


def build_webhook_router(bot: Bot, dispatcher: Dispatcher, settings: Settings) -> APIRouter:
    router = APIRouter()

    @router.post(WEBHOOK_PATH)
    async def telegram_webhook(
        request: Request,
        x_telegram_bot_api_secret_token: Annotated[str | None, Header()] = None,
    ) -> Response:
        secret = settings.webhook_secret
        if not secret or not hmac.compare_digest(
            x_telegram_bot_api_secret_token or "",
            secret,
        ):
            logger.warning("Отклонён запрос webhook: неверный secret token")
            raise HTTPException(status_code=403, detail="Forbidden")

        update = Update.model_validate(await request.json())
        await dispatcher.feed_update(bot, update)
        return Response(status_code=200)

    return router
