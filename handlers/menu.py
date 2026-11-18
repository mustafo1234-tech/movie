from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from utils.i18n import t

router = Router()


@router.message(Command("cancel"))
async def cancel_state(message: Message, state: FSMContext, lang: str = "uz", **kwargs) -> None:
    await state.clear()
    await message.answer(t(lang, "msg.cancelled"))


@router.callback_query()
async def unknown_callback(callback: CallbackQuery, lang: str = "uz", **kwargs) -> None:
    await callback.answer(t(lang, "msg.invalid_callback"))
