import pytest

from config import settings
from database import requests as db
from handlers.admin import allowed
from utils.helpers import is_admin


@pytest.mark.asyncio
async def test_admin_only_access(monkeypatch):
    monkeypatch.setattr(settings, "admin_ids", "4242")
    from types import SimpleNamespace

    admin_event = SimpleNamespace(from_user=SimpleNamespace(id=4242))
    user_event = SimpleNamespace(from_user=SimpleNamespace(id=1))

    assert is_admin(4242) is True
    assert is_admin(1) is False
    assert allowed(admin_event) is True
    assert allowed(user_event) is False


@pytest.mark.asyncio
async def test_admin_statistics(session):
    from services.statistics import overall_stats

    await db.get_or_create_user(session, 7001)
    await db.get_or_create_user(session, 7002)
    stats = await overall_stats(session)
    assert stats["total"] == 2
    assert stats["status"] == "online"


@pytest.mark.asyncio
async def test_find_user_by_id(session):
    await db.get_or_create_user(session, 8001, "finder")
    found = await db.find_users(session, "8001")
    assert len(found) == 1
    assert found[0].telegram_id == 8001
