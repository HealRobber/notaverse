import asyncio
from contextlib import asynccontextmanager
from typing import Optional

try:
    from redis.asyncio import Redis
except Exception:
    Redis = None  # type: ignore


class _LocalLock:
    def __init__(self):
        self._lock = asyncio.Lock()

    async def __aenter__(self):
        await self._lock.acquire()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._lock.release()


@asynccontextmanager
async def acquire_lock(redis_url: Optional[str], key: str, ttl_seconds: int = 900):
    if redis_url and Redis:
        client = Redis.from_url(redis_url)
        lock = client.lock(name=key, timeout=ttl_seconds, blocking_timeout=0)
        have_lock = await lock.acquire(blocking=False)
        try:
            if not have_lock:
                yield None
            else:
                yield lock
        finally:
            if have_lock:
                try:
                    await lock.release()
                except Exception:
                    pass
            await client.aclose()
    else:
        lock = _LocalLock()
        async with lock:
            yield lock
