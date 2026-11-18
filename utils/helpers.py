import html
import re
import unicodedata
from datetime import datetime
from difflib import SequenceMatcher

from config import settings


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", value or "").casefold().strip()
    text = re.sub(r"[ \t\r\n\f\v]+", " ", text)
    text = re.sub(r"\s+([,.:;!?])", r"\1", text)
    return text


def similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, normalize_text(left), normalize_text(right)).ratio()


def escape_html(value: object) -> str:
    if value is None:
        return ""
    return html.escape(str(value), quote=False)


def truncate(value: str, limit: int = 900) -> str:
    value = value or ""
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 1)].rstrip() + "…"


def format_vote(value: object) -> str:
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        return "—"
    if number <= 0:
        return "—"
    return f"{number:.1f}"


def format_date(value: object) -> str:
    if not value:
        return "—"
    text = str(value)
    try:
        return datetime.strptime(text, "%Y-%m-%d").strftime("%d.%m.%Y")
    except ValueError:
        return text


def format_runtime(minutes: object) -> str:
    try:
        total = int(minutes or 0)
    except (TypeError, ValueError):
        return "—"
    if total <= 0:
        return "—"
    hours, rest = divmod(total, 60)
    if hours:
        return f"{hours} soat {rest} daqiqa"
    return f"{rest} daqiqa"


def join_names(items: list[str] | None, limit: int = 6) -> str:
    if not items:
        return "—"
    return ", ".join(items[:limit])


def chunk_list(items: list, size: int) -> list[list]:
    size = max(1, size)
    return [items[index : index + size] for index in range(0, len(items), size)]


def is_admin(telegram_id: int) -> bool:
    return telegram_id in settings.admin_id_list


def media_title(item: dict) -> str:
    return str(item.get("title") or item.get("name") or "—")


def media_year(item: dict) -> str:
    date_value = item.get("release_date") or item.get("first_air_date") or ""
    return str(date_value)[:4] or "—"


def media_type_of(item: dict) -> str:
    mt = str((item or {}).get("media_type") or "").lower()
    if mt in {"movie", "tv"}:
        return mt
    if item.get("first_air_date") or (item.get("name") and not item.get("title")):
        return "tv"
    return "movie"
