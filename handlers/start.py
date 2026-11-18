from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from keyboards.main import main_menu
from utils.helpers import escape_html, is_admin
from utils.i18n import labels, t

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, lang: str = "uz", **kwargs) -> None:
    name = escape_html((message.from_user.first_name if message.from_user else "") or "do'stim")
    await message.answer(
        t(lang, "msg.welcome", name=name),
        reply_markup=main_menu(lang, is_admin(message.from_user.id if message.from_user else 0)),
    )


@router.message(Command("help"))
async def cmd_help(message: Message, lang: str = "uz", **kwargs) -> None:
    await message.answer(t(lang, "msg.about"), reply_markup=main_menu(lang, is_admin(message.from_user.id)))


@router.message(F.text.in_(labels("menu.about")))
async def cmd_about(message: Message, lang: str = "uz", **kwargs) -> None:
    await message.answer(t(lang, "msg.about"))


@router.callback_query(F.data == "home")
async def go_home(callback: CallbackQuery, lang: str = "uz", **kwargs) -> None:
    await callback.answer()
    await callback.message.answer(
        t(lang, "menu.main"),
        reply_markup=main_menu(lang, is_admin(callback.from_user.id)),
    )
