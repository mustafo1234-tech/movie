import asyncio

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import settings
from database import requests as db
from keyboards.admin import admin_menu, broadcast_confirm, users_keyboard
from services import statistics
from states.user import AdminStates
from utils.helpers import escape_html, is_admin
from utils.i18n import labels, t
from utils.pagination import pagination_store

router = Router()


def allowed(event) -> bool:
    user = getattr(event, "from_user", None)
    return bool(user and is_admin(user.id))


async def deny(target, lang: str) -> None:
    if isinstance(target, CallbackQuery):
        await target.answer()
        await target.message.answer(t(lang, "msg.not_admin"))
    else:
        await target.answer(t(lang, "msg.not_admin"))


@router.message(Command("admin"))
@router.message(F.text.in_(labels("menu.admin")))
async def admin_entry(message: Message, lang: str = "uz", **kwargs) -> None:
    if not allowed(message):
        await deny(message, lang)
        return
    await message.answer(t(lang, "msg.admin_menu"), reply_markup=admin_menu(lang))


@router.callback_query(F.data == "adm:menu")
async def admin_back(callback: CallbackQuery, lang: str = "uz", **kwargs) -> None:
    await callback.answer()
    if not allowed(callback):
        await callback.message.answer(t(lang, "msg.not_admin"))
        return
    await callback.message.answer(t(lang, "msg.admin_menu"), reply_markup=admin_menu(lang))


@router.callback_query(F.data == "adm:stats")
async def admin_stats(callback: CallbackQuery, lang: str = "uz", session=None, **kwargs) -> None:
    await callback.answer()
    if not allowed(callback):
        await callback.message.answer(t(lang, "msg.not_admin"))
        return
    data = await statistics.overall_stats(session)
    await callback.message.answer(t(lang, "msg.stats_text", **data))


@router.callback_query(F.data.startswith("adm:period:"))
async def admin_period(callback: CallbackQuery, lang: str = "uz", session=None, **kwargs) -> None:
    await callback.answer()
    if not allowed(callback):
        await callback.message.answer(t(lang, "msg.not_admin"))
        return
    try:
        days = int(callback.data.split(":", 2)[2])
    except (ValueError, AttributeError):
        return
    data = await statistics.period_stats(session, days)
    period_key = {1: "day", 7: "week", 30: "month"}.get(days, "week")
    await callback.message.answer(
        t(lang, "msg.stats_period", period=t(lang, f"msg.period.{period_key}"), **data)
    )


async def render_users(target, lang: str, session, page: int = 1) -> None:
    users, total = await db.list_users(session, limit=settings.page_size, offset=(page - 1) * settings.page_size)
    if not users:
        await answer_users_empty(target, lang)
        return
    token = pagination_store.save([u.telegram_id for u in users], "pgu", total=total)
    pages = max(1, (total + settings.page_size - 1) // settings.page_size)
    lines = [t(lang, "msg.users_title", total=total), ""]
    for user in users:
        username = f"@{user.username}" if user.username else "вЂ”"
        lines.append(
            f"вЂў <code>{user.telegram_id}</code> | {escape_html(username)} | {user.language} | {user.created_at:%d.%m.%Y}"
        )

    await target.answer(
        "\n".join(lines), reply_markup=users_keyboard(lang, token, page, pages), parse_mode="HTML"
    )


async def answer_users_empty(target, lang: str) -> None:
    await target.answer(t(lang, "msg.empty_list"))


@router.callback_query(F.data == "adm:users:1")
async def admin_users(callback: CallbackQuery, lang: str = "uz", session=None, **kwargs) -> None:
    await callback.answer()
    if not allowed(callback):
        await callback.message.answer(t(lang, "msg.not_admin"))
        return
    await render_users(callback.message, lang, session)


@router.callback_query(F.data.startswith("pgu:"))
async def admin_users_page(callback: CallbackQuery, lang: str = "uz", session=None, **kwargs) -> None:
    await callback.answer()
    if not allowed(callback):
        await callback.message.answer(t(lang, "msg.not_admin"))
        return
    try:
        _, _, raw_page = callback.data.split(":", 2)
        page = int(raw_page)
    except (ValueError, AttributeError):
        return
    await render_users(callback.message, lang, session, page)


@router.callback_query(F.data == "adm:find")
async def admin_find_prompt(
    callback: CallbackQuery, state: FSMContext, lang: str = "uz", **kwargs
) -> None:
    await callback.answer()
    if not allowed(callback):
        await callback.message.answer(t(lang, "msg.not_admin"))
        return
    await state.set_state(AdminStates.waiting_user_search)
    await callback.message.answer(t(lang, "msg.user_search_prompt"))


@router.message(AdminStates.waiting_user_search)
async def admin_find_result(
    message: Message, state: FSMContext, lang: str = "uz", session=None, **kwargs
) -> None:
    if not allowed(message):
        await state.clear()
        await deny(message, lang)
        return
    await state.clear()
    users = await db.find_users(session, message.text or "")
    if not users:
        await message.answer(t(lang, "msg.user_not_found"))
        return
    lines = [t(lang, "msg.users_title", total=len(users)), ""]
    for user in users:
        lines.append(f"вЂў <code>{user.telegram_id}</code> | {escape_html(user.username or 'вЂ”')} | {user.language}")
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.callback_query(F.data == "adm:broadcast")
async def broadcast_prompt(
    callback: CallbackQuery, state: FSMContext, lang: str = "uz", **kwargs
) -> None:
    await callback.answer()
    if not allowed(callback):
        await callback.message.answer(t(lang, "msg.not_admin"))
        return
    await state.set_state(AdminStates.waiting_broadcast)
    await callback.message.answer(t(lang, "msg.broadcast_prompt"))


@router.message(AdminStates.waiting_broadcast)
async def broadcast_preview(
    message: Message, state: FSMContext, bot: Bot, lang: str = "uz", session=None, **kwargs
) -> None:
    if not allowed(message):
        await state.clear()
        await deny(message, lang)
        return
    total = await db.count_users(session)
    await state.update_data(
        from_chat_id=message.chat.id,
        message_id=message.message_id,
        text=message.text or "",
    )
    await message.answer(
        t(lang, "msg.broadcast_confirm", count=total), reply_markup=broadcast_confirm(lang)
    )


@router.callback_query(F.data == "bconfirm")
async def broadcast_send(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    lang: str = "uz",
    session=None,
    **kwargs,
) -> None:
    await callback.answer()
    if not allowed(callback):
        await callback.message.answer(t(lang, "msg.not_admin"))
        return
    data = await state.get_data()
    await state.clear()
    users = await db.list_users(session, limit=100000)
    sent = 0
    failed = 0
    for user in users[0]:
        try:
            if data.get("message_id") and data.get("from_chat_id"):
                await bot.copy_message(
                    chat_id=user.telegram_id,
                    from_chat_id=data["from_chat_id"],
                    message_id=data["message_id"],
                )
            else:
                await bot.send_message(chat_id=user.telegram_id, text=data.get("text", ""))
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.04)
    await callback.message.edit_text(t(lang, "msg.broadcast_done", sent=sent, failed=failed))


@router.callback_query(F.data == "bcancel")
async def broadcast_cancel(callback: CallbackQuery, state: FSMContext, lang: str = "uz", **kwargs) -> None:
    await callback.answer()
    if not allowed(callback):
        await callback.message.answer(t(lang, "msg.not_admin"))
        return
    await state.clear()
    await callback.message.answer(t(lang, "msg.broadcast_cancelled"))


@router.callback_query(F.data == "adm:settings")
async def admin_settings(callback: CallbackQuery, lang: str = "uz", **kwargs) -> None:
    await callback.answer()
    if not allowed(callback):
        await callback.message.answer(t(lang, "msg.not_admin"))
        return
    tmdb_status = "TVmaze (public API)"
    await callback.message.answer(
        t(
            lang,
            "msg.settings_text",
            page_size=settings.page_size,
            tmdb=tmdb_status,
            admins=len(settings.admin_id_list),
        )
    )


@router.callback_query(F.data == "adm:status")
async def admin_status(callback: CallbackQuery, lang: str = "uz", **kwargs) -> None:
    await callback.answer()
    if not allowed(callback):
        await callback.message.answer(t(lang, "msg.not_admin"))
        return
    data = await statistics.bot_status()
    await callback.message.answer(t(lang, "msg.status_text", **data))

