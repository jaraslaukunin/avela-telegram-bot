from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> dict[str, object]:
    # TODO: сюда добавятся проверки БД и внешних сервисов, когда они появятся.
    return {"status": "ok", "checks": {}}
