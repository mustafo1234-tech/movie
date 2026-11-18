from config import settings
from database import requests as db
from services.tmdb import TMDBError, tmdb
from utils.logger import log


def deduplicate(items: list[dict]) -> list[dict]:
    seen: set[tuple[str, int]] = set()
    result: list[dict] = []
    for item in items:
        mt = str(item.get("media_type") or "").lower()
        if mt in {"movie", "tv"}:
            kind = mt
        elif item.get("first_air_date") or (item.get("name") and not item.get("title")):
            kind = "tv"
        else:
            kind = "movie"
        key = (kind, int(item.get("id") or 0))
        if key[1] <= 0 or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


async def recommendations_for_user(session, user_id: int, language: str, limit: int = 15) -> list[dict]:
    collected: list[dict] = []
    genre_ids = await db.get_favorite_genres(session, user_id)

    favorites, _ = await db.list_favorites(session, user_id, limit=10)
    watched, _ = await db.list_watched(session, user_id, limit=10)

    seeds: list[tuple[str, int]] = []
    for item in favorites[:3]:
        seeds.append((item.media_type, item.movie_id))
    for item in watched[:3]:
        seeds.append((item.media_type, item.movie_id))

    for media_type, item_id in seeds:
        try:
            collected.extend(await tmdb.recommendations(media_type, item_id, language))
        except TMDBError as exc:
            log.debug("Recommendations skipped: %s", exc)
        try:
            collected.extend(await tmdb.similar(media_type, item_id, language))
        except TMDBError as exc:
            log.debug("Similar skipped: %s", exc)

    if genre_ids:
        try:
            discover = await tmdb.discover_movies(
                language=language,
                genre_ids=genre_ids,
                sort_by="popularity.desc",
                vote_count_gte=50,
            )
            collected.extend(discover.get("results", []))
        except TMDBError as exc:
            log.debug("Genre discovery skipped: %s", exc)

    if not collected:
        try:
            popular = await tmdb.popular_movies(language=language)
            collected.extend(popular.get("results", []))
        except TMDBError as exc:
            log.warning("Popular fallback failed: %s", exc)

    return deduplicate(collected)[: limit or settings.page_size]
