from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from handlers.movies import show_detail
from keyboards.movies import genres_keyboard, random_keyboard
from services.tmdb import TMDBError, tmdb
from states.user import RandomStates
from utils.i18n import labels, t
from utils.logger import log

router = Router()


async def show_random(target, lang: str, genre_id: int | None, session, user) -> None:
    try:
        item = await tmdb.random_movie(genre_id, lang)
    except TMDBError:
        await target.answer(t(lang, "msg.api_error"))
        return
    if not item:
        await target.answer(t(lang, "msg.empty_list"))
        return
    kind = "tv" if item.get("name") else "movie"
    await show_detail(target, kind, int(item["id"]), lang, session, user)


@router.message(F.text.in_(labels("menu.random")))
async def random_menu(message: Message, lang: str = "uz", **kwargs) -> None:
    await message.answer(t(lang, "msg.random_title"), reply_markup=random_keyboard(lang))


@router.callback_query(F.data == "rnd:0")
async def random_movie_callback(
    callback: CallbackQuery, lang: str = "uz", session=None, db_user=None, **kwargs
) -> None:
    await callback.answer()
    if session is None or db_user is None:
        return
    await show_random(callback.message, lang, None, session, db_user)


@router.callback_query(F.data == "rndgenre")
async def random_genre_menu(callback: CallbackQuery, state: FSMContext, lang: str = "uz", **kwargs) -> None:
    await callback.answer()
    await state.set_state(RandomStates.selecting)
    await state.update_data(selected=[])
    await callback.message.answer(t(lang, "msg.genres_title"), reply_markup=genres_keyboard(lang))


@router.callback_query(RandomStates.selecting, F.data.startswith("gen:"))
async def random_toggle_genre(callback: CallbackQuery, state: FSMContext, lang: str = "uz", **kwargs) -> None:
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
        log.debug("Random genre keyboard edit skipped: %s", type(exc).__name__)


@router.callback_query(RandomStates.selecting, F.data == "gdone")
async def random_by_genre(
    callback: CallbackQuery,
    state: FSMContext,
    lang: str = "uz",
    session=None,
    db_user=None,
    **kwargs,
) -> None:
    await callback.answer()
    data = await state.get_data()
    selected = data.get("selected") or []
    await state.clear()
    if session is None or db_user is None:
        return
    genre_id = int(selected[0]) if selected else None
    await show_random(callback.message, lang, genre_id, session, db_user)
