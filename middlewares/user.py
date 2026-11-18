from aiogram import BaseMiddleware

from database import requests as db
from database.engine import AsyncSessionLocal
from utils.logger import log


class UserMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        telegram_user = getattr(event, "from_user", None)
        if telegram_user is None:
            return await handler(event, data)
        try:
            async with AsyncSessionLocal() as session:
                user = await db.get_or_create_user(
                    session,
                    telegram_user.id,
                    telegram_user.username,
                    telegram_user.full_name or "",
                )
                await db.touch_user(session, user)
                data["session"] = session
                data["db_user"] = user
                data["lang"] = user.language
                return await handler(event, data)
        except Exception as exc:
            log.error("User middleware failed: %s", type(exc).__name__)
            data.setdefault("lang", "uz")
            return await handler(event, data)
