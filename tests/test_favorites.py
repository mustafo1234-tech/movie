from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from database import requests as db
from handlers.favorites import toggle_favorite


@pytest.mark.asyncio
async def test_add_and_remove_favorite(session):
    user = await db.get_or_create_user(session, 3001)
    assert await db.add_favorite(session, user.id, 123, "movie") is True
    assert await db.add_favorite(session, user.id, 123, "movie") is False
    assert await db.is_favorite(session, user.id, 123, "movie") is True

    items, total = await db.list_favorites(session, user.id)
    assert total == 1
    assert items[0].movie_id == 123

    assert await db.remove_favorite(session, user.id, 123, "movie") is True
    assert await db.remove_favorite(session, user.id, 123, "movie") is False


@pytest.mark.asyncio
async def test_toggle_favorite_handler(session):
    user = await db.get_or_create_user(session, 3002)
    callback = MagicMock()
    callback.data = "fav:movie:456"
    callback.from_user = SimpleNamespace(id=3002)
    callback.answer = AsyncMock()
    callback.message = MagicMock()
    callback.message.edit_reply_markup = AsyncMock()

    await toggle_favorite(callback, lang="uz", session=session, db_user=user)
    assert await db.is_favorite(session, user.id, 456, "movie") is True

    await toggle_favorite(callback, lang="uz", session=session, db_user=user)
    assert await db.is_favorite(session, user.id, 456, "movie") is False
