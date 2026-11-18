from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from database import requests as db
from handlers.movies import send_results
from keyboards.movies import detail_keyboard
from services.cache import cache
from services.presentation import answerable, trailer_url, watch_link
from services.tmdb import TMDBError, tmdb
from utils.i18n import labels, t
from utils.logger import log
from utils.pagination import paginate, pagination_store

router = Router()


async def load_favorite_items(session, user_id: int, lang: str) -> list[dict]:
    rows, _ = await db.list_favorites(session, user_id, limit=60)
    items: list[dict] = []
    for row in rows:
        kind = row.media_type
        try:
            details = await cache.get_or_set(
                f"detail:{kind}:{row.movie_id}:{lang}",
                lambda kind=kind, item_id=row.movie_id: tmdb.details(kind, item_id, lang),
            )
        except TMDBError:
            continue
        if details:
            details["media_type"] = kind
            items.append(details)
    return items


async def show_favorites(target, session, user, lang: str) -> None:
    items = await load_favorite_items(session, user.id, lang)
    if not items:
        await answerable(target).answer(t(lang, "msg.favorites_empty"))
        return
    token = pagination_store.save(items, "fvp", title=t(lang, "msg.favorites_title"))
    page_items, pages, page = paginate(items, 1)
    from keyboards.search import generic_pagination

    keyboard = generic_pagination(lang, token, page, pages)
    await send_results(
        answerable(target),
        lang,
        t(lang, "msg.favorites_title"),
        page_items,
        token,
        page,
        pages,
        keyboard,
        "fvp",
    )


@router.message(F.text.in_(labels("menu.favorites")))
async def favorites_menu(
    message: Message, lang: str = "uz", session=None, db_user=None, **kwargs
) -> None:
    if session is None or db_user is None:
        return
    await show_favorites(message, session, db_user, lang)


@router.callback_query(F.data.startswith("fvp:"))
async def favorites_page(callback: CallbackQuery, lang: str = "uz", **kwargs) -> None:
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
    page_items, pages, page = paginate(items, page)
    from keyboards.search import generic_pagination

    await send_results(
        answerable(callback),
        lang,
        t(lang, "msg.favorites_title"),
        page_items,
        token,
        page,
        pages,
        generic_pagination(lang, token, page, pages),
        "fvp",
    )


@router.callback_query(F.data.startswith("fav:"))
async def toggle_favorite(
    callback: CallbackQuery, lang: str = "uz", session=None, db_user=None, **kwargs
) -> None:
    await callback.answer()
    if session is None or db_user is None:
        return
    try:
        _, kind, raw_id = callback.data.split(":", 2)
        item_id = int(raw_id)
        if kind not in {"movie", "tv"}:
            raise ValueError
    except (ValueError, AttributeError):
        await answerable(callback).answer(t(lang, "msg.invalid_callback"))
        return
    added = await db.add_favorite(session, db_user.id, item_id, kind)
    if not added:
        await db.remove_favorite(session, db_user.id, item_id, kind)
    message = t(lang, "msg.favorite_added" if added else "msg.favorite_removed")
    await callback.answer(message)
    details = await cache.get(f"detail:{kind}:{item_id}:{lang}") or {}
    if details:
        try:
            await callback.message.edit_reply_markup(
                reply_markup=detail_keyboard(
                    lang,
                    kind,
                    item_id,
                    added,
                    await db.is_watched(session, db_user.id, item_id, kind),
                    trailer_url(details),
                    watch_link(details),
                    bool(details.get("backdrop_path")),
                )
            )
        except Exception as exc:
            log.debug("Favorite keyboard update skipped: %s", type(exc).__name__)
