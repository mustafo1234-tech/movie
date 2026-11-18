from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from handlers.movies import send_results
from keyboards.search import generic_pagination
from services.recommendations import recommendations_for_user
from services.tmdb import TMDBError, tmdb
from utils.i18n import labels, t
from utils.pagination import paginate, pagination_store

router = Router()


async def show_recommendations(target, session, user, lang: str) -> None:
    try:
        items = await recommendations_for_user(session, user.id, lang)
    except TMDBError:
        await target.answer(t(lang, "msg.api_error"))
        return
    if not items:
        await target.answer(t(lang, "msg.recommend_empty"))
        return
    token = pagination_store.save(items, "rcp", title=t(lang, "msg.recommend_title"))
    page_items, pages, page = paginate(items, 1)
    await send_results(
        target,
        lang,
        t(lang, "msg.recommend_title"),
        page_items,
        token,
        page,
        pages,
        generic_pagination(lang, token, page, pages),
        "rcp",
    )


@router.message(F.text.in_(labels("menu.recommendations")))
async def recommendations_menu(
    message: Message, lang: str = "uz", session=None, db_user=None, **kwargs
) -> None:
    if session is None or db_user is None:
        return
    await show_recommendations(message, session, db_user, lang)


@router.callback_query(F.data.startswith("rec:"))
async def item_recommendations(callback: CallbackQuery, lang: str = "uz", **kwargs) -> None:
    await callback.answer()
    try:
        _, kind, raw_id, raw_page = callback.data.split(":", 3)
        item_id, page = int(raw_id), int(raw_page)
        items = await tmdb.recommendations(kind, item_id, lang, page)
    except (ValueError, AttributeError, TMDBError):
        await callback.message.answer(t(lang, "msg.api_error"))
        return
    if not items:
        await callback.message.answer(t(lang, "msg.recommend_empty"))
        return
    token = pagination_store.save(items, "rcp", title=t(lang, "msg.recommend_title"))
    page_items, pages, current = paginate(items, 1)
    await send_results(
        callback.message,
        lang,
        t(lang, "msg.recommend_title"),
        page_items,
        token,
        current,
        pages,
        generic_pagination(lang, token, current, pages),
        "rcp",
    )


@router.callback_query(F.data.startswith("rcp:"))
async def recommendations_page(callback: CallbackQuery, lang: str = "uz", **kwargs) -> None:
    await callback.answer()
    try:
        _, token, raw_page = callback.data.split(":", 2)
        page = int(raw_page)
    except (ValueError, AttributeError):
        await callback.message.answer(t(lang, "msg.invalid_callback"))
        return
    items = pagination_store.get(token)
    if not items:
        await callback.message.answer(t(lang, "msg.invalid_callback"))
        return
    page_items, pages, page = paginate(items, page)
    await send_results(
        callback.message,
        lang,
        t(lang, "msg.recommend_title"),
        page_items,
        token,
        page,
        pages,
        generic_pagination(lang, token, page, pages),
        "rcp",
    )
