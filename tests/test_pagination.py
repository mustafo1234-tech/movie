from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from database import requests as db
from handlers.watched import toggle_watched
from utils.pagination import PaginationStore, paginate


@pytest.mark.asyncio
async def test_watched_flow(session):
    user = await db.get_or_create_user(session, 4001)
    assert await db.add_watched(session, user.id, 550, "movie") is True
    assert await db.add_watched(session, user.id, 550, "movie") is False
    stored, total = await db.list_watched(session, user.id)
    assert total == 1
    assert stored[0].movie_id == 550
    assert await db.remove_watched(session, user.id, 550, "movie") is True
    assert await db.is_watched(session, user.id, 550, "movie") is False


@pytest.mark.asyncio
async def test_watched_handler(session):
    user = await db.get_or_create_user(session, 4002)
    callback = MagicMock()
    callback.data = "wat:tv:1396"
    callback.from_user = SimpleNamespace(id=4002)
    callback.answer = AsyncMock()
    callback.message = MagicMock()
    callback.message.edit_reply_markup = AsyncMock()

    await toggle_watched(callback, lang="ru", session=session, db_user=user)
    assert await db.is_watched(session, user.id, 1396, "tv") is True


def test_pagination_math():
    page_items, pages, current = paginate(list(range(12)), 99, per_page=5)
    assert pages == 3
    assert current == 3
    assert page_items == [10, 11]


def test_pagination_store():
    store = PaginationStore(ttl=60)
    token = store.save([{"id": 1}], "pg", title="Test")
    assert store.get(token)[0]["id"] == 1
    assert store.prefix(token) == "pg"
    assert store.meta(token)["title"] == "Test"
    store.drop(token)
    assert store.get(token) is None
