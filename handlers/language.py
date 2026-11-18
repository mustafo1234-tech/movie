from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from database import requests as db
from keyboards.main import language_keyboard, main_menu
from utils.helpers import is_admin
from utils.i18n import labels, t

router = Router()


@router.message(Command("language"))
@router.message(F.text.in_(labels("menu.language")))
async def choose_language(message: Message, lang: str = "uz", **kwargs) -> None:
    await message.answer(t(lang, "msg.language_prompt"), reply_markup=language_keyboard())


@router.callback_query(F.data.startswith("lang:"))
async def set_new_language(
    callback: CallbackQuery, lang: str = "uz", session=None, db_user=None, **kwargs
) -> None:
    await callback.answer()
    new_lang = callback.data.split(":", 1)[1]
    if new_lang not in {"uz", "ru"}:
        await callback.message.answer(t(lang, "msg.invalid_callback"))
        return
    if session is not None and db_user is not None:
        await db.set_language(session, db_user, new_lang)
    await callback.message.answer(
        t(new_lang, "msg.language_saved"),
        reply_markup=main_menu(new_lang, is_admin(callback.from_user.id)),
    )
