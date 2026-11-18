from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import requests as db
from handlers.movies import send_results
from keyboards.movies import catalog_keyboard, genres_keyboard
from services.tmdb import TMDBError, tmdb
from states.user import GenreStates
from utils.i18n import labels, t
from utils.logger import log
from utils.pagination import paginate, pagination_store

router = Router()


@router.message(F.text.in_(labels("menu.genres")))
async def genres_menu(message: Message, state: FSMContext, lang: str = "uz", **kwargs) -> None:
    await state.set_state(GenreStates.selecting)
    await state.update_data(selected=[])
    await message.answer(t(lang, "msg.genres_title"), reply_markup=genres_keyboard(lang))


@router.callback_query(GenreStates.selecting, F.data.startswith("gen:"))
async def toggle_genre(callback: CallbackQuery, state: FSMContext, lang: str = "uz", **kwargs) -> None:
    await callback.answer()
    try:
        genre_id = int(callback.data.split(":", 1)[1])
    except (ValueError, AttributeError):
        return
    data = await state.get_data()
    selected = set(data.get("selected") or [])
    if genre_id in selected:
        selected.remove(genre_id)
    else:
        selected.add(genre_id)
    await state.update_data(selected=sorted(selected))
    try:
        await callback.message.edit_reply_markup(reply_markup=genres_keyboard(lang, selected))
    except Exception as exc:
        log.debug("Genre keyboard edit skipped: %s", type(exc).__name__)


@router.callback_query(GenreStates.selecting, F.data == "gdone")
async def apply_genres(
    callback: CallbackQuery,
    state: FSMContext,
    lang: str = "uz",
    session=None,
    db_user=None,
    **kwargs,
) -> None:
    await callback.answer()
    data = await state.get_data()
    selected = [int(item) for item in (data.get("selected") or [])]
    await state.clear()
    if session is not None and db_user is not None:
        await db.set_favorite_genres(session, db_user.id, selected)
    if not selected:
        await callback.message.answer(t(lang, "msg.genres_title"), reply_markup=genres_keyboard(lang))
        return
    try:
        result = await tmdb.discover_movies(
            language=lang,
            genre_ids=selected,
            sort_by="popularity.desc",
            vote_count_gte=20,
        )
    except TMDBError:
        await callback.message.answer(t(lang, "msg.api_error"))
        return
    items = [item for item in result.get("results", []) if isinstance(item, dict)]
    if not items:
        await callback.message.answer(t(lang, "msg.empty_list"))
        return
    title = t(lang, "msg.genres_chosen", genres=len(selected))
    token = pagination_store.save(items, "lst", title=title, catalog="genre")
    page_items, pages, page = paginate(items, 1)
    keyboard = catalog_keyboard(lang, token, "genre", page, pages, 1, 1, len(items))
    await send_results(callback.message, lang, title, page_items, token, page, pages, keyboard, "lst")
