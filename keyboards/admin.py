from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from utils.i18n import t


def _inline(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def admin_menu(lang: str) -> InlineKeyboardMarkup:
    rows = [
        [_inline(t(lang, "btn.stats"), "adm:stats")],
        [_inline(t(lang, "btn.users"), "adm:users:1"), _inline("🔍 " + t(lang, "btn.users"), "adm:find")],
        [_inline("📅 7", "adm:period:7"), _inline("🗓 30", "adm:period:30"), _inline("📆 1", "adm:period:1")],
        [_inline(t(lang, "btn.send_broadcast"), "adm:broadcast")],
        [_inline(t(lang, "btn.settings"), "adm:settings"), _inline(t(lang, "btn.status"), "adm:status")],
        [_inline(t(lang, "btn.main_menu"), "home")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def broadcast_confirm(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                _inline(t(lang, "btn.yes"), "bconfirm"),
                _inline(t(lang, "btn.no"), "bcancel"),
            ]
        ]
    )


def users_keyboard(lang: str, token: str, page: int, pages: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    navigation: list[InlineKeyboardButton] = []
    if page > 1:
        navigation.append(_inline(t(lang, "btn.prev"), f"pgu:{token}:{page - 1}"))
    if page < pages:
        navigation.append(_inline(t(lang, "btn.next"), f"pgu:{token}:{page + 1}"))
    if navigation:
        rows.append(navigation)
    rows.append([_inline(t(lang, "btn.back"), "adm:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
