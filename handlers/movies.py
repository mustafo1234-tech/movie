from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from config import settings
from database import requests as db
from keyboards.movies import (
    catalog_keyboard,
    detail_keyboard,
    items_keyboard,
)
from services.cache import cache
from services.presentation import (
    answerable,
    detail_caption,
    send_poster,
    send_results,
    trailer_url,
    watch_link,
)
from services.tmdb import TMDBError, tmdb
from utils.helpers import escape_html, media_title
from utils.i18n import labels, t
from utils.pagination import paginate, pagination_store

router = Router()

CATALOG_TITLES: dict[str, str] = {
    "popular_movies": "section.popular_movies",
    "top_movies": "section.top_movies",
    "new_movies": "section.new_movies",
    "now_playing": "section.now_playing",
    "popular_series": "section.popular_series",
    "top_series": "section.top_series",
    "popular_anime": "section.popular_anime",
    "top_anime": "section.top_anime",
    "new_anime": "section.new_anime",
    "best_animation": "section.best_animation",
}

MOVIE_SECTIONS = ["popular_movies", "top_movies", "new_movies", "now_playing"]


async def fetch_catalog(key: str, language: str, page: int) -> dict:
    if key == "popular_movies":
        return await tmdb.popular_movies(page, language)
    if key == "top_movies":
        return await tmdb.top_rated_movies(page, language)
    if key == "new_movies":
        return await tmdb.discover_movies(
            page=page,
            language=language,
            sort_by="primary_release_date.desc",
            release_lte="2026-12-31",
            vote_count_gte=20,
        )
    if key == "now_playing":
        return await tmdb.now_playing(page, language)
    if key == "popular_series":
        return await tmdb.popular_tv(page, language)
    if key == "top_series":
        return await tmdb.top_rated_tv(page, language)
    if key == "popular_anime":
        return await tmdb.discover_tv(
            page=page, language=language, genre_ids=[16], original_language="ja"
        )
    if key == "top_anime":
        return await tmdb.discover_tv(
            page=page,
            language=language,
            genre_ids=[16],
            original_language="ja",
            sort_by="vote_average.desc",
            vote_count_gte=100,
        )
    if key == "new_anime":
        return await tmdb.discover_tv(
            page=page,
            language=language,
            genre_ids=[16],
            original_language="ja",
            sort_by="first_air_date.desc",
        )
    if key == "best_animation":
        return await tmdb.discover_movies(
            page=page,
            language=language,
            genre_ids=[16],
            sort_by="vote_average.desc",
            vote_count_gte=100,
        )
    return {"results": [], "total_pages": 1}


async def send_catalog(target, language: str, key: str, api_page: int = 1) -> None:
    title = t(language, CATALOG_TITLES.get(key, "section.movies"))
    try:
        data = await cache.get_or_set(
            f"catalog:{key}:{api_page}:{language}",
            lambda: fetch_catalog(key, language, api_page),
        )
    except TMDBError:
        await answerable(target).answer(t(language, "msg.api_error"))
        return
    items = [item for item in data.get("results", []) if isinstance(item, dict)]
    if not items:
        await answerable(target).answer(t(language, "msg.empty_list"))
        return
    api_pages = min(max(1, int(data.get("total_pages") or 1)), 500)
    token = pagination_store.save(
        items,
        "lst",
        title=title,
        catalog=key,
        api_page=api_page,
        api_pages=api_pages,
    )
    page_items, local_pages, page = paginate(items, 1)
    keyboard = catalog_keyboard(
        language, token, key, page, local_pages, api_page, api_pages, len(items)
    )
    await send_results(
        answerable(target), language, title, page_items, token, page, local_pages, keyboard, "lst"
    )


def movie_sections_keyboard(language: str):
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    rows = [
        [
            InlineKeyboardButton(text=t(language, "section.popular_movies"), callback_data="cat:popular_movies"),
            InlineKeyboardButton(text=t(language, "section.top_movies"), callback_data="cat:top_movies"),
        ],
        [
            InlineKeyboardButton(text=t(language, "section.new_movies"), callback_data="cat:new_movies"),
            InlineKeyboardButton(text=t(language, "section.now_playing"), callback_data="cat:now_playing"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def show_detail(target, media_type: str, item_id: int, language: str, session, user) -> None:
    kind = "tv" if media_type == "tv" else "movie"
    try:
        details = await cache.get_or_set(
            f"detail:{kind}:{item_id}:{language}",
            lambda: tmdb.details(kind, item_id, language),
        )
    except TMDBError:
        await answerable(target).answer(t(language, "msg.api_error"))
        return
    if not details:
        await answerable(target).answer(t(language, "msg.empty_list"))
        return
    favorite = await db.is_favorite(session, user.id, item_id, kind)
    watched = await db.is_watched(session, user.id, item_id, kind)
    keyboard = detail_keyboard(
        language,
        kind,
        item_id,
        favorite,
        watched,
        trailer_url(details),
        watch_link(details),
        bool(details.get("backdrop_path")),
    )
    await send_poster(answerable(target), details, detail_caption(details, language, kind), keyboard)


@router.message(F.text.in_(labels("menu.movies")))
async def movies_menu(message: Message, lang: str = "uz", **kwargs) -> None:
    await message.answer(t(lang, "section.movies"), reply_markup=movie_sections_keyboard(lang))


@router.message(F.text.in_(labels("menu.popular")))
async def popular_movies(message: Message, lang: str = "uz", **kwargs) -> None:
    await send_catalog(message, lang, "popular_movies")


@router.message(F.text.in_(labels("menu.top")))
async def top_movies(message: Message, lang: str = "uz", **kwargs) -> None:
    await send_catalog(message, lang, "top_movies")


@router.callback_query(F.data.startswith("cat:"))
async def catalog_callback(callback: CallbackQuery, lang: str = "uz", **kwargs) -> None:
    await callback.answer()
    key = callback.data.split(":", 1)[1]
    if key not in CATALOG_TITLES:
        await answerable(callback).answer(t(lang, "msg.invalid_callback"))
        return
    await send_catalog(callback, lang, key)


@router.callback_query(F.data.startswith("catnext:") | F.data.startswith("catprev:"))
async def catalog_page_callback(callback: CallbackQuery, lang: str = "uz", **kwargs) -> None:
    await callback.answer()
    try:
        action, key, raw_page = callback.data.split(":", 2)
        page = int(raw_page)
    except (ValueError, AttributeError):
        await answerable(callback).answer(t(lang, "msg.invalid_callback"))
        return
    if action == "catprev":
        page = max(1, page)
    await send_catalog(callback, lang, key, page)


@router.callback_query(F.data.startswith("lst:"))
async def catalog_local_page(callback: CallbackQuery, lang: str = "uz", **kwargs) -> None:
    await callback.answer()
    try:
        _, token, raw_page = callback.data.split(":", 2)
        page = int(raw_page)
    except (ValueError, AttributeError):
        await answerable(callback).answer(t(lang, "msg.invalid_callback"))
        return
    items = pagination_store.get(token)
    if not items:
        await answerable(callback).answer(t(lang, "msg.invalid_callback"))
        return
    meta = pagination_store.meta(token)
    page_items, local_pages, page = paginate(items, page)
    keyboard = catalog_keyboard(
        lang,
        token,
        str(meta.get("catalog", "popular_movies")),
        page,
        local_pages,
        int(meta.get("api_page", 1)),
        int(meta.get("api_pages", 1)),
        len(items),
    )
    await send_results(
        answerable(callback),
        lang,
        str(meta.get("title", "")),
        page_items,
        token,
        page,
        local_pages,
        keyboard,
        "lst",
    )


@router.callback_query(F.data.startswith("d:"))
async def detail_callback(
    callback: CallbackQuery, lang: str = "uz", session=None, db_user=None, **kwargs
) -> None:
    await callback.answer()
    if session is None or db_user is None:
        return
    try:
        _, kind, raw_id = callback.data.split(":", 2)
        item_id = int(raw_id)
    except (ValueError, AttributeError):
        await answerable(callback).answer(t(lang, "msg.invalid_callback"))
        return
    await show_detail(callback, kind, item_id, lang, session, db_user)


@router.callback_query(F.data.startswith("itm:"))
async def item_callback(
    callback: CallbackQuery, lang: str = "uz", session=None, db_user=None, **kwargs
) -> None:
    await callback.answer()
    if session is None or db_user is None:
        return
    try:
        _, token, raw_index = callback.data.split(":", 2)
        index = int(raw_index)
        items = pagination_store.get(token)
        if not items or index < 0 or index >= len(items):
            raise ValueError
        item = items[index]
        item_id = int(item.get("id") or 0)
        mt = str(item.get("media_type") or "").lower()
        if mt in {"movie", "tv"}:
            kind = mt
        elif item.get("first_air_date") or (item.get("name") and not item.get("title")):
            kind = "tv"
        else:
            kind = "movie"
    except (ValueError, AttributeError, TypeError):
        await answerable(callback).answer(t(lang, "msg.invalid_callback"))
        return
    await show_detail(callback, kind, item_id, lang, session, db_user)


@router.callback_query(F.data.startswith("bd:"))
async def backdrop_callback(callback: CallbackQuery, lang: str = "uz", **kwargs) -> None:
    await callback.answer()
    try:
        _, kind, raw_id = callback.data.split(":", 2)
        item_id = int(raw_id)
        details = await tmdb.details(kind, item_id, lang, append=False)
        image = tmdb.image_url(details.get("backdrop_path"), "original")
    except (ValueError, AttributeError, TMDBError):
        image = None
    if not image:
        await answerable(callback).answer(t(lang, "msg.no_poster"))
        return
    await answerable(callback).answer_photo(photo=image, caption=t(lang, "btn.backdrop"))


@router.callback_query(F.data.startswith("sim:"))
async def similar_callback(callback: CallbackQuery, lang: str = "uz", **kwargs) -> None:
    await callback.answer()
    try:
        _, kind, raw_id, raw_page = callback.data.split(":", 3)
        item_id, page = int(raw_id), int(raw_page)
    except (ValueError, AttributeError):
        await answerable(callback).answer(t(lang, "msg.invalid_callback"))
        return
    try:
        items = await tmdb.similar(kind, item_id, lang, page)
    except TMDBError:
        await answerable(callback).answer(t(lang, "msg.api_error"))
        return
    if not items:
        await answerable(callback).answer(t(lang, "msg.empty_list"))
        return
    token = pagination_store.save(items, "smp", title=t(lang, "msg.similar_title"))
    page_items, pages, current = paginate(items, 1)

    keyboard = items_keyboard(lang, token, current, pages, len(page_items), "smp")
    await send_results(
        answerable(callback),
        lang,
        t(lang, "msg.similar_title"),
        page_items,
        token,
        current,
        pages,
        keyboard,
        "smp",
    )


@router.callback_query(F.data.startswith("smp:"))
async def similar_page(callback: CallbackQuery, lang: str = "uz", **kwargs) -> None:
    await callback.answer()
    try:
        _, token, raw_page = callback.data.split(":", 2)
        page = int(raw_page)
    except (ValueError, AttributeError):
        await answerable(callback).answer(t(lang, "msg.invalid_callback"))
        return
    items = pagination_store.get(token)
    if not items:
        await answerable(callback).answer(t(lang, "msg.invalid_callback"))
        return
    page_items, pages, current = paginate(items, page)

    keyboard = items_keyboard(lang, token, current, pages, len(page_items), "smp")
    await send_results(
        answerable(callback),
        lang,
        t(lang, "msg.similar_title"),
        page_items,
        token,
        current,
        pages,
        keyboard,
        "smp",
    )


def cast_text(items: list[dict], lang: str) -> str:
    lines = [t(lang, "msg.cast_title"), ""]
    for index, person in enumerate(items, start=1):
        name = escape_html(person.get("name") or "—")
        character = escape_html(person.get("character") or person.get("job") or "")
        lines.append(f"{index}. {name}" + (f" — {character}" if character else ""))
    return "\n".join(lines)


@router.callback_query(F.data.startswith("cast:"))
async def cast_callback(callback: CallbackQuery, lang: str = "uz", **kwargs) -> None:
    await callback.answer()
    try:
        _, kind, raw_id, raw_page = callback.data.split(":", 3)
        item_id, page = int(raw_id), int(raw_page)
    except (ValueError, AttributeError):
        await answerable(callback).answer(t(lang, "msg.invalid_callback"))
        return
    try:
        credits = await tmdb.credits(kind, item_id, lang)
    except TMDBError:
        await answerable(callback).answer(t(lang, "msg.api_error"))
        return
    cast = [item for item in credits.get("cast", []) if isinstance(item, dict)]
    crew = [
        item
        for item in credits.get("crew", [])
        if isinstance(item, dict) and item.get("job") in {"Director", "Writer", "Producer"}
    ]
    people = cast + crew
    if not people:
        await answerable(callback).answer(t(lang, "msg.cast_empty"))
        return
    token = pagination_store.save(people, "csp", title=t(lang, "msg.cast_title"))
    page_items, pages, current = paginate(people, page)
    keyboard = cast_keyboard(lang, token, current, pages, len(page_items))
    await answerable(callback).answer(
        cast_text(page_items, lang), reply_markup=keyboard, parse_mode="HTML"
    )


def cast_keyboard(lang: str, token: str, page: int, pages: int, count: int):
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    rows: list[list[InlineKeyboardButton]] = []
    buttons = []
    offset = (page - 1) * settings.page_size
    for index in range(offset, offset + count):
        item = pagination_store.get(token)[index]
        buttons.append(
            InlineKeyboardButton(
                text=str(index - offset + 1), callback_data=f"per:{item.get('id')}"
            )
        )
    for start in range(0, len(buttons), 5):
        rows.append(buttons[start : start + 5])
    navigation: list[InlineKeyboardButton] = []
    if page > 1:
        navigation.append(InlineKeyboardButton(text=t(lang, "btn.prev"), callback_data=f"csp:{token}:{page - 1}"))
    if page < pages:
        navigation.append(InlineKeyboardButton(text=t(lang, "btn.next"), callback_data=f"csp:{token}:{page + 1}"))
    if navigation:
        rows.append(navigation)
    rows.append([InlineKeyboardButton(text=t(lang, "btn.main_menu"), callback_data="home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data.startswith("csp:"))
async def cast_page(callback: CallbackQuery, lang: str = "uz", **kwargs) -> None:
    await callback.answer()
    try:
        _, token, raw_page = callback.data.split(":", 2)
        page = int(raw_page)
    except (ValueError, AttributeError):
        await answerable(callback).answer(t(lang, "msg.invalid_callback"))
        return
    people = pagination_store.get(token)
    if not people:
        await answerable(callback).answer(t(lang, "msg.invalid_callback"))
        return
    page_items, pages, current = paginate(people, page)
    await answerable(callback).answer(
        cast_text(page_items, lang),
        reply_markup=cast_keyboard(lang, token, current, pages, len(page_items)),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("per:"))
async def person_callback(callback: CallbackQuery, lang: str = "uz", **kwargs) -> None:
    await callback.answer()
    try:
        person_id = int(callback.data.split(":", 1)[1])
        person = await tmdb.person(person_id, lang)
    except (ValueError, AttributeError, TMDBError):
        await answerable(callback).answer(t(lang, "msg.api_error"))
        return
    lines = [t(lang, "msg.person_title", name=escape_html(person.get("name") or "—")), ""]
    if person.get("birthday"):
        lines.append(f"{t(lang, 'msg.person_birthday')} {escape_html(person['birthday'])}")
    if person.get("place_of_birth"):
        lines.append(f"{t(lang, 'msg.person_place')} {escape_html(person['place_of_birth'])}")
    biography = escape_html(person.get("biography") or "")[:800]
    if biography:
        lines.extend(["", f"{t(lang, 'msg.person_bio')}", biography])
    known = [item for item in (person.get("known_for") or {}).get("results", []) if isinstance(item, dict)]
    if known:
        lines.extend(["", t(lang, "msg.person_known")])
        for item in known[:5]:
            lines.append(f"• {escape_html(media_title(item))}")
    from keyboards.movies import person_keyboard

    await send_poster(answerable(callback), None, "\n".join(lines), person_keyboard(lang))
