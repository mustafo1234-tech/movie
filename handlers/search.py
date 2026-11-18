import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import requests as db
from keyboards.search import results_keyboard
from services.presentation import answerable, send_results
from services.tmdb import TMDBError, tmdb
from states.user import SearchStates
from utils.helpers import media_title, media_year, normalize_text, similarity
from utils.i18n import labels, t
from utils.pagination import paginate, pagination_store

router = Router()

SEARCH_LABELS = labels("menu.search")


def extract_year(query: str) -> tuple[str, int | None]:
    match = re.search(r"\b(19\d{2}|20\d{2})\b", query)
    if not match:
        return query, None
    year = int(match.group(1))
    clean = (query[: match.start()] + " " + query[match.end() :]).strip()
    return clean, year


def deduplicate(items: list[dict]) -> list[dict]:
    seen: set[tuple[str, int]] = set()
    result: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = int(item.get("id") or 0)
        if item_id <= 0:
            continue
        if item.get("media_type") == "person":
            continue
        mt = str(item.get("media_type") or "").lower()
        if mt in {"movie", "tv"}:
            kind = mt
        elif item.get("first_air_date") or (item.get("name") and not item.get("title")):
            kind = "tv"
        else:
            kind = "movie"
        key = (kind, item_id)
        if key in seen:
            continue
        seen.add(key)
        normalized = dict(item)
        normalized["media_type"] = kind
        result.append(normalized)
    return result


def score_item(item: dict, query: str, year: int | None) -> float:
    titles = [
        media_title(item),
        str(item.get("original_title") or ""),
        str(item.get("original_name") or ""),
        str(item.get("title") or ""),
        str(item.get("name") or ""),
    ]
    score = max((similarity(query, title) for title in titles if title), default=0.0)
    if year and media_year(item) == str(year):
        score += 1.0
    return score


async def smart_search(query: str, language: str) -> list[dict]:
    clean, year = extract_year(normalize_text(query))
    if not clean:
        clean = normalize_text(query)
    collected: list[dict] = []
    for lang in dict.fromkeys([language, "en-US", "ru-RU"]):
        try:
            collected.extend(await tmdb.search_multi(clean, lang))
        except TMDBError:
            continue
    for finder in (tmdb.search_movies, tmdb.search_tv):
        try:
            collected.extend(await finder(clean, language, year=year))
        except TMDBError:
            continue
    try:
        people = await tmdb.search_person(clean)
        for person in people:
            collected.extend(person.get("known_for") or [])
    except TMDBError:
        pass

    results = deduplicate(collected)
    results.sort(key=lambda item: score_item(item, clean, year), reverse=True)
    return results[:30]


async def suggestions_for(query: str, language: str) -> list[str]:
    clean, _ = extract_year(normalize_text(query))
    words = [word for word in clean.split() if len(word) >= 3]
    guesses: list[str] = []
    for word in words[:2]:
        try:
            found = await tmdb.search_multi(word, language)
        except TMDBError:
            continue
        for item in found[:3]:
            title = media_title(item)
            if title and title not in guesses:
                guesses.append(title)
    if not guesses and len(words) > 1:
        guesses.append(" ".join(words[:-1]))
    return guesses[:5]


async def run_search(message: Message, query: str, language: str, session, user) -> None:
    clean = normalize_text(query)
    if len(clean) < 2:
        await message.answer(t(language, "msg.search_prompt"))
        return
    await db.add_search_history(session, user.id, query.strip())
    await message.answer(t(language, "msg.searching"))
    try:
        items = await smart_search(clean, language)
    except TMDBError:
        await message.answer(t(language, "msg.api_error"))
        return
    if not items:
        text = t(language, "msg.no_results", query=query.strip())
        try:
            hints = await suggestions_for(clean, language)
        except TMDBError:
            hints = []
        if hints:
            text += "\n\n" + t(language, "msg.suggestions")
            text += "\n" + "\n".join(f"• {hint}" for hint in hints)
        await message.answer(text)
        return
    token = pagination_store.save(items, "pg", title=t(language, "msg.results_title", query=query.strip()))
    page_items, pages, page = paginate(items, 1)
    keyboard = results_keyboard(language, token, page, pages, len(page_items))
    await send_results(
        message,
        language,
        t(language, "msg.results_title", query=query.strip()),
        page_items,
        token,
        page,
        pages,
        keyboard,
    )


@router.message(F.text.in_(SEARCH_LABELS))
async def ask_query(message: Message, state: FSMContext, lang: str = "uz", **kwargs) -> None:
    await state.set_state(SearchStates.waiting_query)
    await message.answer(t(lang, "msg.search_prompt"))


@router.callback_query(F.data == "newsearch")
async def new_search(callback: CallbackQuery, state: FSMContext, lang: str = "uz", **kwargs) -> None:
    await callback.answer()
    await state.set_state(SearchStates.waiting_query)
    await answerable(callback).answer(t(lang, "msg.search_prompt"))


@router.message(SearchStates.waiting_query)
async def search_from_state(
    message: Message, state: FSMContext, lang: str = "uz", session=None, db_user=None, **kwargs
) -> None:
    await state.clear()
    if session is None or db_user is None:
        await message.answer(t(lang, "msg.error_generic"))
        return
    await run_search(message, message.text or "", lang, session, db_user)


@router.callback_query(F.data.startswith("pg:"))
async def search_page(callback: CallbackQuery, lang: str = "uz", **kwargs) -> None:
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
    title = pagination_store.meta(token).get("title") or t(lang, "menu.search")
    keyboard = results_keyboard(lang, token, page, pages, len(page_items))
    await send_results(
        answerable(callback), lang, str(title), page_items, token, page, pages, keyboard
    )


@router.message(F.text)
async def search_any_text(
    message: Message, lang: str = "uz", session=None, db_user=None, **kwargs
) -> None:
    if session is None or db_user is None:
        return
    await run_search(message, message.text or "", lang, session, db_user)
