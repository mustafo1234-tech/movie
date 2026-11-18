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

SECTIONS = ["popular_series", "top_series"]


@router.message(F.text.in_(labels("menu.series")))
async def series_menu(message: Message, lang: str = "uz", **kwargs) -> None:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "section.popular_series"), callback_data="ser:popular_series")],
            [InlineKeyboardButton(text=t(lang, "section.top_series"), callback_data="ser:top_series")],
        ]
    )
    await message.answer(t(lang, "section.series"), reply_markup=keyboard)


@router.callback_query(F.data.startswith("ser:"))
async def series_section(callback: CallbackQuery, lang: str = "uz", **kwargs) -> None:
    await callback.answer()
    key = callback.data.split(":", 1)[1]
    if key not in SECTIONS:
        await callback.message.answer(t(lang, "msg.invalid_callback"))
        return
    await send_catalog(callback, lang, key)
