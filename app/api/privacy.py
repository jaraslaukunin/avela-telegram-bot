"""Право на удаление данных: анонимизация аккаунта по запросу пациента."""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.rate_limit import RateLimiter
from app.db import get_session
from app.models.user import User
from app.schemas import AnonymizationOut
from app.services.privacy import anonymize_user

logger = logging.getLogger(__name__)

DeleteRateLimit = RateLimiter(limit=5)

router = APIRouter(prefix="/privacy", tags=["privacy"])


@router.post("/delete-me", dependencies=[Depends(DeleteRateLimit)])
async def delete_me(
    current: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AnonymizationOut:
    """Удаление персональных данных: запись аккаунта анонимизируется.

    Данные не исчезают бесследно: история записей остаётся обезличенной
    (для клиники), а факт и объём удаления фиксируются в аудите.
    """
    report = await anonymize_user(session, current)
    logger.info(
        "Аккаунт анонимизирован: отменено записей=%s, погашено уведомлений=%s",
        report.cancelled_appointments,
        report.skipped_notifications,
    )
    return AnonymizationOut(
        anonymized=True,
        cancelled_appointments=report.cancelled_appointments,
        skipped_notifications=report.skipped_notifications,
    )
