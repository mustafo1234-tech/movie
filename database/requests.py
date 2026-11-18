from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from database.models import (
    Favorite,
    SearchHistory,
    User,
    UserPreferences,
    Watched,
    utcnow,
)


async def get_user_by_telegram_id(session, telegram_id: int) -> User | None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def create_user(
    session,
    telegram_id: int,
    username: str | None = None,
    full_name: str = "",
    language: str = "uz",
) -> User:
    user = User(
        telegram_id=telegram_id,
        username=username,
        full_name=full_name or "",
        language=language if language in {"uz", "ru"} else "uz",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_or_create_user(
    session,
    telegram_id: int,
    username: str | None = None,
    full_name: str = "",
) -> User:
    user = await get_user_by_telegram_id(session, telegram_id)
    if user is not None:
        updates = False
        if username and user.username != username:
            user.username = username
            updates = True
        if full_name and user.full_name != full_name:
            user.full_name = full_name
            updates = True
        if updates:
            await session.commit()
        return user
    try:
        return await create_user(session, telegram_id, username, full_name)
    except IntegrityError:
        await session.rollback()
        user = await get_user_by_telegram_id(session, telegram_id)
        if user is None:
            raise
        return user


async def touch_user(session, user: User) -> None:
    user.last_active = utcnow()
    await session.commit()


async def set_language(session, user: User, language: str) -> None:
    user.language = language if language in {"uz", "ru"} else "uz"
    await session.commit()


async def add_favorite(session, user_id: int, movie_id: int, media_type: str) -> bool:
    existing = await session.execute(
        select(Favorite).where(
            Favorite.user_id == user_id,
            Favorite.movie_id == movie_id,
            Favorite.media_type == media_type,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return False
    session.add(Favorite(user_id=user_id, movie_id=movie_id, media_type=media_type))
    await session.commit()
    return True


async def remove_favorite(session, user_id: int, movie_id: int, media_type: str) -> bool:
    result = await session.execute(
        select(Favorite).where(
            Favorite.user_id == user_id,
            Favorite.movie_id == movie_id,
            Favorite.media_type == media_type,
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        return False
    await session.delete(item)
    await session.commit()
    return True


async def is_favorite(session, user_id: int, movie_id: int, media_type: str) -> bool:
    result = await session.execute(
        select(Favorite.id).where(
            Favorite.user_id == user_id,
            Favorite.movie_id == movie_id,
            Favorite.media_type == media_type,
        )
    )
    return result.scalar_one_or_none() is not None


async def list_favorites(
    session, user_id: int, limit: int = 5, offset: int = 0
) -> tuple[list[Favorite], int]:
    total = await session.scalar(
        select(func.count()).select_from(Favorite).where(Favorite.user_id == user_id)
    )
    items = (
        await session.execute(
            select(Favorite)
            .where(Favorite.user_id == user_id)
            .order_by(Favorite.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()
    return list(items), int(total or 0)


async def add_watched(session, user_id: int, movie_id: int, media_type: str) -> bool:
    existing = await session.execute(
        select(Watched).where(
            Watched.user_id == user_id,
            Watched.movie_id == movie_id,
            Watched.media_type == media_type,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return False
    session.add(Watched(user_id=user_id, movie_id=movie_id, media_type=media_type))
    await session.commit()
    return True


async def remove_watched(session, user_id: int, movie_id: int, media_type: str) -> bool:
    result = await session.execute(
        select(Watched).where(
            Watched.user_id == user_id,
            Watched.movie_id == movie_id,
            Watched.media_type == media_type,
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        return False
    await session.delete(item)
    await session.commit()
    return True


async def is_watched(session, user_id: int, movie_id: int, media_type: str) -> bool:
    result = await session.execute(
        select(Watched.id).where(
            Watched.user_id == user_id,
            Watched.movie_id == movie_id,
            Watched.media_type == media_type,
        )
    )
    return result.scalar_one_or_none() is not None


async def list_watched(
    session, user_id: int, limit: int = 5, offset: int = 0
) -> tuple[list[Watched], int]:
    total = await session.scalar(
        select(func.count()).select_from(Watched).where(Watched.user_id == user_id)
    )
    items = (
        await session.execute(
            select(Watched)
            .where(Watched.user_id == user_id)
            .order_by(Watched.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()
    return list(items), int(total or 0)


async def add_search_history(session, user_id: int, query: str) -> None:
    session.add(SearchHistory(user_id=user_id, search_query=query[:500]))
    await session.commit()


async def count_searches(session, user_id: int) -> int:
    return int(
        await session.scalar(
            select(func.count()).select_from(SearchHistory).where(SearchHistory.user_id == user_id)
        )
        or 0
    )


async def get_favorite_genres(session, user_id: int) -> list[int]:
    result = await session.execute(
        select(UserPreferences).where(UserPreferences.user_id == user_id)
    )
    preferences = result.scalar_one_or_none()
    if preferences is None or not preferences.favorite_genres:
        return []
    values: list[int] = []
    for part in preferences.favorite_genres.split(","):
        try:
            values.append(int(part))
        except ValueError:
            continue
    return values


async def set_favorite_genres(session, user_id: int, genre_ids: list[int]) -> None:
    result = await session.execute(
        select(UserPreferences).where(UserPreferences.user_id == user_id)
    )
    preferences = result.scalar_one_or_none()
    value = ",".join(str(int(item)) for item in sorted(set(genre_ids)))
    if preferences is None:
        session.add(UserPreferences(user_id=user_id, favorite_genres=value))
    else:
        preferences.favorite_genres = value
    await session.commit()


async def get_user_stats(session, user_id: int) -> dict[str, int]:
    favorites = await session.scalar(
        select(func.count()).select_from(Favorite).where(Favorite.user_id == user_id)
    )
    watched = await session.scalar(
        select(func.count()).select_from(Watched).where(Watched.user_id == user_id)
    )
    searches = await session.scalar(
        select(func.count()).select_from(SearchHistory).where(SearchHistory.user_id == user_id)
    )
    return {
        "favorites": int(favorites or 0),
        "watched": int(watched or 0),
        "searches": int(searches or 0),
    }


async def count_users(session) -> int:
    return int(await session.scalar(select(func.count()).select_from(User)) or 0)


async def count_users_since(session, since: datetime) -> int:
    return int(
        await session.scalar(select(func.count()).select_from(User).where(User.created_at >= since))
        or 0
    )


async def count_active_since(session, since: datetime) -> int:
    return int(
        await session.scalar(
            select(func.count()).select_from(User).where(User.last_active >= since)
        )
        or 0
    )


async def count_searches_since(session, since: datetime) -> int:
    return int(
        await session.scalar(
            select(func.count()).select_from(SearchHistory).where(SearchHistory.created_at >= since)
        )
        or 0
    )


async def list_users(session, limit: int = 10, offset: int = 0) -> tuple[list[User], int]:
    total = await count_users(session)
    items = (
        await session.execute(
            select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
        )
    ).scalars().all()
    return list(items), total


async def find_users(session, term: str, limit: int = 10) -> list[User]:
    clean = (term or "").strip().lstrip("@")
    if not clean:
        return []
    if clean.isdigit():
        result = await session.execute(
            select(User).where(User.telegram_id == int(clean)).limit(limit)
        )
        return list(result.scalars().all())
    pattern = f"%{clean.lower()}%"
    result = await session.execute(
        select(User).where(func.lower(User.username).like(pattern)).limit(limit)
    )
    return list(result.scalars().all())


def since_days(days: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=days)
