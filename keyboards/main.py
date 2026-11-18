from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from utils.i18n import t


def _button(lang: str, key: str) -> KeyboardButton:
    return KeyboardButton(text=t(lang, key))


def main_menu(lang: str, admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [_button(lang, "menu.search"), _button(lang, "menu.movies"), _button(lang, "menu.series")],
        [_button(lang, "menu.anime"), _button(lang, "menu.popular"), _button(lang, "menu.top")],
        [_button(lang, "menu.genres"), _button(lang, "menu.countries"), _button(lang, "menu.random")],
        [_button(lang, "menu.favorites"), _button(lang, "menu.watched"), _button(lang, "menu.recommendations")],
        [_button(lang, "menu.profile"), _button(lang, "menu.language"), _button(lang, "menu.about")],
    ]
    if admin:
        rows.append([_button(lang, "menu.admin")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇿 O'zbek tili", callback_data="lang:uz"),
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
            ]
        ]
    )


def back_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t(lang, "btn.main_menu"), callback_data="home")]]
    )
