from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from handlers.movies import send_catalog
from utils.i18n import labels, t

router = Router()

SECTIONS = ["popular_anime", "top_anime", "new_anime", "best_animation"]


@router.message(F.text.in_(labels("menu.anime")))
async def anime_menu(message: Message, lang: str = "uz", **kwargs) -> None:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "section.popular_anime"), callback_data="anm:popular_anime")],
            [InlineKeyboardButton(text=t(lang, "section.top_anime"), callback_data="anm:top_anime")],
            [InlineKeyboardButton(text=t(lang, "section.new_anime"), callback_data="anm:new_anime")],
            [InlineKeyboardButton(text=t(lang, "section.best_animation"), callback_data="anm:best_animation")],
        ]
    )
    await message.answer(t(lang, "section.anime"), reply_markup=keyboard)


@router.callback_query(F.data.startswith("anm:"))
async def anime_section(callback: CallbackQuery, lang: str = "uz", **kwargs) -> None:
    await callback.answer()
    key = callback.data.split(":", 1)[1]
    if key not in SECTIONS:
        await callback.message.answer(t(lang, "msg.invalid_callback"))
        return
    await send_catalog(callback, lang, key)
