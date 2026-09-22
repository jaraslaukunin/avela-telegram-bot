"""Мини-кэш с временем жизни для редко меняющихся данных.

Справочники (сети, филиалы, услуги, врачи) меняются раз в никогда, а каждый
запрос к Supabase стоит десятки миллисекунд на сетевых round-trip'ах.
Короткий TTL убирает эти обращения почти полностью, при этом свежесть
каталога остаётся приемлемой для администраторов.

Кэш живёт в памяти процесса: при нескольких инстансах backend у каждого
будет свой — для MVP это нормально.
"""
import asyncio
import time
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


def ttl_cache(
    ttl_seconds: float,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Кэширует результат async-функции на ttl_seconds.

    Ключ — аргументы вызова. Значения должны быть неизменяемыми по смыслу
    (обычно pydantic-модели), чтобы кэш не отдавал чужое состояние сессии.
    """

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        cache: dict[tuple[Any, ...], tuple[float, R]] = {}
        lock = asyncio.Lock()

        def cached_value(key: tuple[Any, ...], now: float) -> R | None:
            entry = cache.get(key)
            if entry is None:
                return None
            stored_at, value = entry
            if (now - stored_at) >= ttl_seconds:
                cache.pop(key, None)
                return None
            return value

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            key = (args, tuple(sorted(kwargs.items())))

            hit = cached_value(key, time.monotonic())
            if hit is not None:
                return hit

            # Блокировка не даёт параллельным запросам дублировать работу.
            async with lock:
                hit = cached_value(key, time.monotonic())
                if hit is not None:
                    return hit
                value = await func(*args, **kwargs)
                cache[key] = (time.monotonic(), value)
                return value

        return wrapper

    return decorator
