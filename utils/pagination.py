import secrets
import time
from dataclasses import dataclass

from config import settings


@dataclass
class StoredPage:
    items: list
    prefix: str
    created_at: float
    meta: dict


class PaginationStore:
    def __init__(self, ttl: int = 1800) -> None:
        self.ttl = ttl
        self._items: dict[str, StoredPage] = {}

    def save(self, items: list, prefix: str = "pg", **meta: object) -> str:
        token = secrets.token_urlsafe(6)
        self._items[token] = StoredPage(
            items=list(items), prefix=prefix, created_at=time.time(), meta=dict(meta)
        )
        return token

    def get(self, token: str) -> list | None:
        entry = self._items.get(token)
        if entry is None:
            return None
        if time.time() - entry.created_at > self.ttl:
            self._items.pop(token, None)
            return None
        entry.created_at = time.time()
        return entry.items

    def prefix(self, token: str) -> str:
        entry = self._items.get(token)
        return entry.prefix if entry else "pg"

    def meta(self, token: str) -> dict:
        entry = self._items.get(token)
        return dict(entry.meta) if entry else {}

    def drop(self, token: str) -> None:
        self._items.pop(token, None)

    def cleanup(self) -> None:
        now = time.time()
        expired = [key for key, value in self._items.items() if now - value.created_at > self.ttl]
        for key in expired:
            self._items.pop(key, None)


pagination_store = PaginationStore()


def paginate(items: list, page: int, per_page: int | None = None) -> tuple[list, int, int]:
    per_page = per_page or settings.page_size
    total = max(1, per_page)
    pages = max(1, (len(items) + total - 1) // total)
    current = min(max(1, page), pages)
    start = (current - 1) * total
    return items[start : start + total], pages, current
