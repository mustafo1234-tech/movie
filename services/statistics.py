from datetime import UTC, datetime, timedelta

from config import settings
from database import requests as db
from services.cache import cache


async def overall_stats(session) -> dict:

    now = datetime.now(UTC)
    return {
        "total": await db.count_users(session),
        "today": await db.count_users_since(session, now - timedelta(days=1)),
        "week": await db.count_users_since(session, now - timedelta(days=7)),
        "month": await db.count_users_since(session, now - timedelta(days=30)),
        "active": await db.count_active_since(session, now - timedelta(days=7)),
        "status": "online",
    }


async def period_stats(session, days: int) -> dict:
    return {
        "users": await db.count_users_since(session, db.since_days(days)),
        "searches": await db.count_searches_since(session, db.since_days(days)),
    }


async def bot_status() -> dict:
    uptime = await cache.get("bot:started_at")
    return {
        "uptime": uptime or "—",
        "database": settings.database_url.split(":///")[0],
        "cache": "Redis" if cache._enabled else "memory",
    }
