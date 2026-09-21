"""Тесты middleware и rate limiting (без БД)."""
import httpx
from fastapi import Depends, FastAPI

from app.core.middleware import (
    REQUEST_ID_HEADER,
    RequestIdMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.rate_limit import RateLimiter


def _app(limiter: RateLimiter | None = None) -> FastAPI:
    application = FastAPI()
    application.add_middleware(RequestIdMiddleware)
    application.add_middleware(SecurityHeadersMiddleware)

    dependencies = [Depends(limiter)] if limiter is not None else []

    @application.get("/ping", dependencies=dependencies)
    async def ping() -> dict[str, str]:
        return {"status": "ok"}

    return application


def _client(limiter: RateLimiter | None = None) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=_app(limiter))
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def test_security_headers_are_present() -> None:
    async with _client() as client:
        response = await client.get("/ping")

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"


async def test_request_id_is_generated_and_echoed() -> None:
    async with _client() as client:
        generated = await client.get("/ping")
        provided = await client.get("/ping", headers={REQUEST_ID_HEADER: "abc123"})

    assert generated.headers[REQUEST_ID_HEADER]
    assert provided.headers[REQUEST_ID_HEADER] == "abc123"


async def test_rate_limiter_returns_429_after_limit() -> None:
    limiter = RateLimiter(limit=2, window_seconds=60)

    async with _client(limiter) as client:
        first = await client.get("/ping")
        second = await client.get("/ping")
        third = await client.get("/ping")

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert "Слишком много запросов" in third.json()["detail"]


async def test_rate_limiter_window_expires() -> None:
    limiter = RateLimiter(limit=1, window_seconds=0)

    async with _client(limiter) as client:
        first = await client.get("/ping")
        second = await client.get("/ping")

    assert first.status_code == 200
    assert second.status_code == 200
