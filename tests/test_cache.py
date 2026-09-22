"""Тесты TTL-кэша (без БД)."""
import asyncio

from app.core.cache import ttl_cache


async def test_cache_returns_cached_value() -> None:
    calls = 0

    @ttl_cache(10)
    async def load(key: str) -> str:
        nonlocal calls
        calls += 1
        return f"value-{key}"

    assert await load("a") == "value-a"
    assert await load("a") == "value-a"
    assert calls == 1


async def test_cache_keys_are_independent() -> None:
    calls = 0

    @ttl_cache(10)
    async def load(key: str) -> str:
        nonlocal calls
        calls += 1
        return f"value-{key}"

    assert await load("a") == "value-a"
    assert await load("b") == "value-b"
    assert await load("a") == "value-a"
    assert calls == 2


async def test_cache_expires() -> None:
    calls = 0

    @ttl_cache(0.05)
    async def load() -> str:
        nonlocal calls
        calls += 1
        return "fresh"

    assert await load() == "fresh"
    await asyncio.sleep(0.08)
    assert await load() == "fresh"
    assert calls == 2


async def test_parallel_calls_do_not_duplicate_work() -> None:
    calls = 0

    @ttl_cache(10)
    async def load() -> str:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.02)
        return "value"

    results = await asyncio.gather(load(), load(), load())

    assert results == ["value", "value", "value"]
    assert calls == 1
