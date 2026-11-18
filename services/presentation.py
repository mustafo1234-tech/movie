from urllib.parse import quote_plus

from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import settings
from keyboards.movies import GENRES
from services.tmdb import tmdb
from utils.helpers import (
    escape_html,
    format_date,
    format_runtime,
    format_vote,
    join_names,
    media_title,
    media_year,
    truncate,
)
from utils.i18n import t
from utils.logger import log

_GENRE_MAP = dict(GENRES)


def genre_names(genres: list[dict] | None, lang: str) -> str:
    if not genres:
        return t(lang, "label.no_data")
    names: list[str] = []
    for genre in genres:
        if not isinstance(genre, dict):
            continue
        key = _GENRE_MAP.get(int(genre.get("id") or 0))
        names.append(t(lang, f"genre.{key}") if key else str(genre.get("name") or ""))
    return join_names([name for name in names if name], limit=5)


def trailer_url(details: dict) -> str | None:
    videos = (details.get("videos") or {}).get("results") or []
    for video in videos:
        if not isinstance(video, dict) or video.get("site") != "YouTube":
            continue
        if video.get("type") not in {"Trailer", "Teaser"}:
            continue
        key = video.get("key")
        if key:
            return f"https://www.youtube.com/watch?v={key}"
    title = media_title(details)
    if title and title != "—":
        return f"https://www.youtube.com/results?search_query={quote_plus(title + ' trailer')}"
    return None


def watch_link(details: dict) -> str | None:
    providers = (details.get("watch/providers") or {}).get("results") or {}
    if not isinstance(providers, dict):
        return None
    for region in ("US", "GB", "RU"):
        region_data = providers.get(region)
        if not isinstance(region_data, dict):
            continue
        link = region_data.get("watch_link") or region_data.get("link")
        if link:
            return str(link)
    for region_data in providers.values():
        if isinstance(region_data, dict) and region_data.get("watch_link"):
            return str(region_data["watch_link"])
    return None


def detail_caption(details: dict, lang: str, media_type: str) -> str:
    title = escape_html(media_title(details))
    original = escape_html(details.get("original_title") or details.get("original_name") or "—")
    released = format_date(details.get("release_date") or details.get("first_air_date"))
    rating = format_vote(details.get("vote_average"))
    votes = details.get("vote_count")
    rating_text = rating if rating == "—" else f"{rating} ({votes})" if votes else rating
    runtime = format_runtime(details.get("runtime")) if media_type == "movie" else "—"
    countries = details.get("production_countries") or []
    country_names = join_names(
        [item.get("name", "") for item in countries if isinstance(item, dict)], limit=4
    )
    credits = details.get("credits") or {}
    cast = [
        item.get("name", "")
        for item in (credits.get("cast") or [])[:8]
        if isinstance(item, dict)
    ]
    directors = [
        item.get("name", "")
        for item in (credits.get("crew") or [])
        if isinstance(item, dict) and item.get("job") == "Director"
    ]
    overview = truncate(escape_html(details.get("overview") or ""), 850) or t(lang, "label.no_data")

    lines = [
        f"🎬 <b>{title}</b>",
        "",
        f"{t(lang, 'label.original')}: {original}",
        f"{t(lang, 'label.release')}: {released}",
        f"{t(lang, 'label.genres')}: {genre_names(details.get('genres'), lang)}",
        f"{t(lang, 'label.rating')}: {rating_text}",
    ]
    if media_type == "movie":
        lines.append(f"{t(lang, 'label.runtime')}: {runtime}")
    else:
        lines.append(f"{t(lang, 'label.seasons')}: {details.get('number_of_seasons') or '—'}")
        lines.append(f"{t(lang, 'label.episodes')}: {details.get('number_of_episodes') or '—'}")
        lines.append(f"{t(lang, 'label.status')}: {escape_html(details.get('status') or '—')}")
    lines.extend(
        [
            f"{t(lang, 'label.country')}: {country_names}",
            f"{t(lang, 'label.director')}: {join_names(directors, limit=3)}",
            f"{t(lang, 'label.cast')}: {join_names(cast, limit=6)}",
            "",
            f"{t(lang, 'label.overview')}:",
            overview,
        ]
    )
    return "\n".join(lines)


def search_caption(item: dict, index: int, lang: str) -> str:
    mt = str(item.get("media_type") or "").lower()
    if mt in {"movie", "tv"}:
        media_type = mt
    elif item.get("first_air_date") or (item.get("name") and not item.get("title")):
        media_type = "tv"
    else:
        media_type = "movie"
    title = escape_html(media_title(item))
    kind = t(lang, "label.tv" if media_type == "tv" else "label.movie")
    return (
        f"{index + 1}. <b>{title}</b>\n"
        f"📅 {media_year(item)} | ⭐ {format_vote(item.get('vote_average'))} | {kind}"
    )


def answerable(event):
    return event.message if isinstance(event, CallbackQuery) else event


async def send_poster(
    message: Message,
    item: dict | None,
    caption: str,
    reply_markup=None,
) -> Message:
    photo = tmdb.image_url((item or {}).get("poster_path"), "w500")
    if photo:
        try:
            return await message.answer_photo(
                photo=photo, caption=caption, reply_markup=reply_markup, parse_mode="HTML"
            )
        except Exception as exc:
            log.debug("Poster send failed, falling back to text: %s", type(exc).__name__)
    return await message.answer(text=caption, reply_markup=reply_markup, parse_mode="HTML")


async def send_results(
    message: Message,
    lang: str,
    title: str,
    items: list[dict],
    token: str,
    page: int,
    pages: int,
    keyboard,
    prefix: str = "pg",
) -> None:
    header = f"{title}\n{t(lang, 'msg.results_count', count=len(items), page=page, pages=pages)}"
    offset = (page - 1) * settings.page_size
    for index, item in enumerate(items):
        caption = search_caption(item, index, lang)
        item_title = media_title(item)
        label = (
            f"📄 {truncate(item_title, 32)}" if item_title and item_title != "—" else t(lang, "btn.details")
        )
        item_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=label, callback_data=f"itm:{token}:{offset + index}"
                    )
                ]
            ]
        )
        url = tmdb.image_url(item.get("poster_path"), "w500")
        sent = False
        if url:
            try:
                await message.answer_photo(
                    photo=url,
                    caption=caption[:1024],
                    reply_markup=item_keyboard,
                    parse_mode="HTML",
                )
                sent = True
            except Exception as exc:
                log.debug("Poster send failed, falling back to text: %s", type(exc).__name__)
        if not sent:
            await message.answer(
                text=caption, reply_markup=item_keyboard, parse_mode="HTML"
            )
    await message.answer(text=header, reply_markup=keyboard, parse_mode="HTML")
