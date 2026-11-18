import json
import time

from config import settings
from utils.logger import log


class Cache:
    def __init__(self) -> None:
        self._local: dict[str, tuple[float, str]] = {}
        self._redis = None
        self._enabled = False
        self.ttl = settings.cache_ttl

    async def initialize(self) -> None:
        if not settings.redis_url:
            return
        try:
            import redis.asyncio as redis

            self._redis = redis.from_url(settings.redis_url, decode_responses=True)
            await self._redis.ping()
            self._enabled = True
            log.info("Redis cache connected")
        except Exception as exc:
            log.warning("Redis unavailable, using in-memory cache: %s", type(exc).__name__)
            self._redis = None
            self._enabled = False

    async def get(self, key: str):
        if self._enabled and self._redis is not None:
            try:
                value = await self._redis.get(key)
                if value is not None:
                    return json.loads(value)
            except Exception as exc:
                log.debug("Redis get failed: %s", type(exc).__name__)
        entry = self._local.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if expires_at < time.time():
            self._local.pop(key, None)
            return None
        return json.loads(value)

    async def set(self, key: str, value, ttl: int | None = None) -> None:
        lifetime = ttl or self.ttl
        encoded = json.dumps(value, ensure_ascii=False, default=str)
        self._local[key] = (time.time() + lifetime, encoded)
        if self._enabled and self._redis is not None:
            try:
                await self._redis.set(key, encoded, ex=lifetime)
            except Exception as exc:
                log.debug("Redis set failed: %s", type(exc).__name__)

    async def get_or_set(self, key: str, factory, ttl: int | None = None):
        cached = await self.get(key)
        if cached is not None:
            return cached
        value = await factory()
        await self.set(key, value, ttl)
        return value

    async def delete(self, key: str) -> None:
        self._local.pop(key, None)
        if self._enabled and self._redis is not None:
            try:
                await self._redis.delete(key)
            except Exception as exc:
                log.debug("Redis delete failed: %s", type(exc).__name__)

    async def close(self) -> None:
        if self._redis is not None:
            try:
                await self._redis.close()
            except Exception as exc:
                log.debug("Redis close failed: %s", type(exc).__name__)


cache = Cache()
