"""Публичные health-роуты и состояние компонентов для status page."""
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.rate_limit import RateLimiter
from app.db import get_session
from app.models.service import ServiceHeartbeat

StatusRateLimit = RateLimiter(limit=120)

router = APIRouter(dependencies=[Depends(StatusRateLimit)])

HEARTBEAT_STALE_AFTER = timedelta(minutes=5)


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness: процесс жив. Наружу — минимум информации."""
    return {"status": "ok", "time": datetime.now(UTC).isoformat()}


@router.get("/ready")
async def ready(session: AsyncSession = Depends(get_session)) -> dict[str, object]:
    """Readiness: проверяем БД — единственную внешнюю зависимость API."""
    checks: dict[str, str] = {}
    try:
        await session.execute(text("select 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "failed"

    status = "ok" if all(value == "ok" for value in checks.values()) else "degraded"
    return {"status": status, "checks": checks}


@router.get("/status")
async def public_status(session: AsyncSession = Depends(get_session)) -> dict[str, object]:
    """Состояние компонентов для status page (avela.jaraslau.dev/status/).

    Не раскрывает секреты, строки подключения, адреса и данные пациентов.
    """
    settings = get_settings()
    now = datetime.now(UTC)

    database = "ok"
    worker = "unknown"
    try:
        await session.execute(text("select 1"))
        heartbeat = await session.get(ServiceHeartbeat, "worker")
        if heartbeat is None:
            worker = "not_started"
        else:
            heartbeat_at = heartbeat.updated_at
            if heartbeat_at.tzinfo is None:
                heartbeat_at = heartbeat_at.replace(tzinfo=UTC)
            worker = "ok" if now - heartbeat_at <= HEARTBEAT_STALE_AFTER else "degraded"
    except Exception:
        database = "failed"
        worker = "unknown"

    return {
        "status": "ok" if database == "ok" else "degraded",
        "time": now.isoformat(),
        "components": {
            "api": "ok",
            "database": database,
            "worker": worker,
            "telegram_delivery": "webhook" if settings.webhook_mode else "polling",
        },
    }
