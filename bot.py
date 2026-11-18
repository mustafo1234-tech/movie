import asyncio
from datetime import UTC, datetime

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, ErrorEvent

from config import settings
from database.engine import close_db, init_db
from handlers import (
    admin,
    anime,
    countries,
    favorites,
    genres,
    language,
    menu,
    movies,
    profile,
    random_movie,
    recommendations,
    search,
    series,
    start,
    watched,
)
from middlewares.user import UserMiddleware
from services.cache import cache
from services.tmdb import tmdb
from utils.logger import log, setup_logging


def create_storage() -> BaseStorage:
    if cache._enabled and settings.redis_url:
        try:
            from aiogram.fsm.storage.redis import RedisStorage

            return RedisStorage.from_url(settings.redis_url)
        except Exception as exc:
            log.warning("Redis FSM storage unavailable, using memory: %s", type(exc).__name__)
    return MemoryStorage()


async def register_routers(dp: Dispatcher) -> None:
    for router in (
        start.router,
        language.router,
        movies.router,
        series.router,
        anime.router,
        genres.router,
        countries.router,
        favorites.router,
        watched.router,
        recommendations.router,
        random_movie.router,
        profile.router,
        admin.router,
        search.router,
        menu.router,
    ):
        dp.include_router(router)


async def setup_bot(dp: Dispatcher) -> None:
    dp.update.middleware(UserMiddleware())

    async def on_error(event: ErrorEvent) -> None:
        log.exception("Unhandled update error: %s", type(event.exception).__name__)

    dp.errors.register(on_error)

    await register_routers(dp)


async def main() -> None:
    setup_logging(settings.log_level)
    if not settings.bot_token:
        log.error("BOT_TOKEN is not set. Copy .env.example to .env and fill required values.")
        return

    await init_db()
    await cache.initialize()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=create_storage())

    await cache.set(
        "bot:started_at",
        datetime.now(UTC).strftime("%d.%m.%Y %H:%M:%S UTC"),
        ttl=315360000,
    )
    await setup_bot(dp)

    try:
        await bot.set_my_commands(
            [
                BotCommand(command="start", description="Start / Boshlash"),
                BotCommand(command="help", description="About / Bot haqida"),
                BotCommand(command="language", description="Language / Til"),
                BotCommand(command="admin", description="Admin panel"),
                BotCommand(command="cancel", description="Cancel / Bekor qilish"),
            ]
        )
        log.info("MovieUz Bot started (polling, TVmaze)")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        await tmdb.close()
        await cache.close()
        await close_db()
        log.info("MovieUz Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
