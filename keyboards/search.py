from aiogram.types import InlineKeyboardMarkup

from keyboards.movies import items_keyboard, list_keyboard


def results_keyboard(
    lang: str, token: str, page: int, pages: int, count: int
) -> InlineKeyboardMarkup:
    return items_keyboard(lang, token, page, pages, count, prefix="pg")


def search_results_pagination(
    lang: str, token: str, page: int, pages: int, count: int
) -> InlineKeyboardMarkup:
    return results_keyboard(lang, token, page, pages, count)


def generic_pagination(
    lang: str, token: str, page: int, pages: int
) -> InlineKeyboardMarkup:
    return list_keyboard(lang, token, page, pages)
