import pytest

from database import requests as db


@pytest.mark.asyncio
async def test_user_registration(session):
    user = await db.get_or_create_user(session, 1001, "aziz", "Aziz")
    assert user.id is not None
    assert user.language == "uz"

    again = await db.get_or_create_user(session, 1001, "aziz", "Aziz")
    assert again.id == user.id
    assert await db.count_users(session) == 1


@pytest.mark.asyncio
async def test_language_persistence(session):
    user = await db.get_or_create_user(session, 1002)
    await db.set_language(session, user, "ru")
    found = await db.get_user_by_telegram_id(session, 1002)
    assert found.language == "ru"


@pytest.mark.asyncio
async def test_search_history_counter(session):
    user = await db.get_or_create_user(session, 1003)
    await db.add_search_history(session, user.id, "Avatar")
    await db.add_search_history(session, user.id, "Titanic")
    assert await db.count_searches(session, user.id) == 2


@pytest.mark.asyncio
async def test_user_preferences(session):
    user = await db.get_or_create_user(session, 1004)
    await db.set_favorite_genres(session, user.id, [28, 18, 28])
    assert await db.get_favorite_genres(session, user.id) == [18, 28]
