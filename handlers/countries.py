from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from handlers.movies import send_results
from keyboards.movies import COUNTRIES, catalog_keyboard, countries_keyboard
from services.tmdb import TMDBError, tmdb
from utils.i18n import labels, t
from utils.pagination import paginate, pagination_store

router = Router()

COUNTRY_MAP = {key: (code, language) for key, code, language in COUNTRIES}


@router.message(F.text.in_(labels("menu.countries")))
async def countries_menu(message: Message, lang: str = "uz", **kwargs) -> None:
    await message.answer(t(lang, "msg.countries_title"), reply_markup=countries_keyboard(lang))


@router.callback_query(F.data.startswith("ctry:"))
async def country_selected(callback: CallbackQuery, lang: str = "uz", **kwargs) -> None:
    await callback.answer()
    key = callback.data.split(":", 1)[1]
    if key not in COUNTRY_MAP:
        await callback.message.answer(t(lang, "msg.invalid_callback"))
        return
    code, original_language = COUNTRY_MAP[key]
    title = t(lang, "section.country", country=t(lang, f"country.{key}"))
    try:
        result = await tmdb.discover_movies(
            language=lang,
            country=code,
            original_language=original_language,
            sort_by="popularity.desc",
        )
    except TMDBError:
        await callback.message.answer(t(lang, "msg.api_error"))
        return
    items = [item for item in result.get("results", []) if isinstance(item, dict)]
    if not items:
        await callback.message.answer(t(lang, "msg.empty_list"))
        return
    token = pagination_store.save(items, "lst", title=title, catalog=f"country:{key}")
    page_items, pages, page = paginate(items, 1)
    keyboard = catalog_keyboard(lang, token, f"country:{key}", page, pages, 1, 1, len(items))
    await send_results(callback.message, lang, title, page_items, token, page, pages, keyboard, "lst")
