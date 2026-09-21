"""Простой rate limiting для чувствительных endpoint'ов.

MVP: счётчики живут в памяти процесса. Если backend поедет на несколько
инстансов, понадобится общий счётчик (Redis) — до тех пор лимиты работают
на одном инстансе.
"""
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

WINDOW_SECONDS = 60
MAX_KEYS = 10_000


class RateLimiter:
    """Скользящее окно: не больше `limit` запросов за окно на клиента и путь."""

    def __init__(self, limit: int, window_seconds: int = WINDOW_SECONDS) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def _key(self, request: Request) -> str:
        client = request.client.host if request.client else "unknown"
        return f"{client}:{request.url.path}"

    def _prune(self, key: str, now: float) -> deque[float]:
        hits = self._hits[key]
        while hits and now - hits[0] > self.window_seconds:
            hits.popleft()
        return hits

    async def __call__(self, request: Request) -> None:
        now = time.monotonic()
        key = self._key(request)

        if len(self._hits) > MAX_KEYS:
            self._hits = defaultdict(deque, {k: v for k, v in self._hits.items() if v})

        hits = self._prune(key, now)
        if len(hits) >= self.limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Слишком много запросов, попробуйте позже",
            )
        hits.append(now)
