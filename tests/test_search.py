
import pytest

from handlers.search import deduplicate, extract_year, score_item, smart_search
from services.tmdb import TMDBClient, TMDBError
from utils.helpers import normalize_text, similarity


def test_normalize_and_similarity():
    assert normalize_text("  The   MATRIX\n ") == "the matrix"
    assert similarity("avatar", "Avatar ") == 1.0
    assert similarity("avatar", "titanic") < 0.4


def test_extract_year():
    text, year = extract_year("Avatar 2009")
    assert year == 2009
    assert text == "Avatar"


def test_deduplicate_keeps_unique_media():
    items = [
        {"id": 1, "title": "A", "media_type": "movie"},
        {"id": 1, "title": "A", "media_type": "movie"},
        {"id": 1, "name": "A series", "media_type": "tv"},
        {"id": 2, "media_type": "person"},
    ]
    result = deduplicate(items)
    assert len(result) == 2
    assert {item["media_type"] for item in result} == {"movie", "tv"}


def test_score_boosts_matching_year():
    item = {"id": 1, "title": "Avatar", "release_date": "2009-12-18"}
    assert score_item(item, "avatar", 2009) > score_item(item, "avatar", 2022)


@pytest.mark.asyncio
async def test_tmdb_api_error_is_managed():
    import httpx

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"status_message": "server error"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url=TMDBClient.BASE_URL) as client:
        tmdb = TMDBClient(api_key="test", max_retries=0, client=client)
        with pytest.raises(TMDBError):
            await tmdb.search_multi("Avatar", "uz")


@pytest.mark.asyncio
async def test_tmdb_success_parses_results():
    import httpx

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": [{"id": 1, "title": "Avatar"}]})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url=TMDBClient.BASE_URL
    ) as client:
        tmdb = TMDBClient(api_key="test", client=client)
        result = await tmdb.search_multi("Avatar", "uz")
        assert result[0]["title"] == "Avatar"


@pytest.mark.asyncio
async def test_smart_search_merges_and_sorts(monkeypatch):
    from services import tmdb as tmdb_module

    async def fake_multi(query, language, page=1):
        return [{"id": 2, "title": "Avatar: The Way of Water", "media_type": "movie"}]

    async def fake_movies(query, language, page=1, year=None):
        return [{"id": 1, "title": "Avatar", "media_type": "movie", "release_date": "2009-12-18"}]

    async def fake_tv(query, language, page=1, year=None):
        return []

    async def fake_person(query, page=1):
        return []

    monkeypatch.setattr(tmdb_module.tmdb, "search_multi", fake_multi)
    monkeypatch.setattr(tmdb_module.tmdb, "search_movies", fake_movies)
    monkeypatch.setattr(tmdb_module.tmdb, "search_tv", fake_tv)
    monkeypatch.setattr(tmdb_module.tmdb, "search_person", fake_person)

    result = await smart_search("Avatar 2009", "uz")
    assert len(result) == 2
    assert result[0]["id"] == 1
