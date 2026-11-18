from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from handlers.start import cmd_start
from keyboards.main import main_menu
from utils.i18n import t


@pytest.mark.asyncio
async def test_start_sends_welcome():
    message = MagicMock()
    message.from_user = SimpleNamespace(id=555, first_name="Aziz")
    message.answer = AsyncMock()

    await cmd_start(message, lang="uz")

    text = message.answer.call_args.args[0]
    assert "MovieUz Bot" in text
    assert "Aziz" in text
    assert message.answer.call_args.kwargs["reply_markup"] is not None


def test_main_menu_contains_all_sections():
    markup = main_menu("uz", admin=True)
    texts = {button.text for row in markup.keyboard for button in row}
    for key in (
        "menu.search",
        "menu.movies",
        "menu.series",
        "menu.anime",
        "menu.popular",
        "menu.top",
        "menu.genres",
        "menu.countries",
        "menu.favorites",
        "menu.watched",
        "menu.random",
        "menu.recommendations",
        "menu.language",
        "menu.about",
        "menu.admin",
    ):
        assert t("uz", key) in texts


@pytest.mark.asyncio
async def test_language_change_handler(monkeypatch):
    from config import settings
    from handlers.language import set_new_language

    monkeypatch.setattr(settings, "admin_ids", "111")
    user = SimpleNamespace(id=222, language="uz")
    session = MagicMock()
    session.commit = AsyncMock()

    callback = MagicMock()
    callback.from_user = SimpleNamespace(id=222)
    callback.data = "lang:ru"
    callback.answer = AsyncMock()
    callback.message = MagicMock()
    callback.message.answer = AsyncMock()

    from database import requests as db

    async def fake_set_language(*args, **kwargs):
        user.language = "ru"

    monkeypatch.setattr(db, "set_language", fake_set_language)

    await set_new_language(callback, lang="uz", session=session, db_user=user)

    assert user.language == "ru"
    sent = callback.message.answer.call_args.args[0]
    assert sent == t("ru", "msg.language_saved")
