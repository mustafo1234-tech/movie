from aiogram import F, Router
from aiogram.types import Message

from database import requests as db
from utils.i18n import labels, t

router = Router()


@router.message(F.text.in_(labels("menu.profile")))
async def profile(
    message: Message, lang: str = "uz", session=None, db_user=None, **kwargs
) -> None:
    if session is None or db_user is None:
        return
    stats = await db.get_user_stats(session, db_user.id)
    created = db_user.created_at.strftime("%d.%m.%Y") if db_user.created_at else "—"
    text = t(
        lang,
        "msg.profile_text",
        telegram_id=db_user.telegram_id,
        created_at=created,
        favorites=stats["favorites"],
        watched=stats["watched"],
        searches=stats["searches"],
        language=db_user.language.upper(),
    )
    await message.answer(text, parse_mode="HTML")
