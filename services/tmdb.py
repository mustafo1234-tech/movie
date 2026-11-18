import asyncio
import random
import re
from datetime import date, datetime
from html import unescape
from typing import Any

import httpx

from config import settings


class TMDBError(Exception):
    """Compatibility error type for API failures."""


_GENRE_MAP = {
    28: "Action",
    12: "Adventure",
    16: "Animation",
    35: "Comedy",
    80: "Crime",
    99: "Documentary",
    18: "Drama",
    10751: "Family",
    14: "Fantasy",
    36: "History",
    27: "Horror",
    10402: "Music",
    9648: "Mystery",
    10749: "Romance",
    878: "Sci-Fi",
    53: "Thriller",
    10752: "War",
    37: "Western",
}

_LANG_NAME = {
    "ja": "japanese",
    "en": "english",
    "ko": "korean",
    "ru": "russian",
    "tr": "turkish",
    "zh": "chinese",
    "hi": "hindi",
    "fr": "french",
}


def _strip_html(value: str | None) -> str:
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", "", value)
    return unescape(text).strip()


def _tv_image(show: dict, kind: str = "medium") -> str | None:
    image = show.get("image") or {}
    if not isinstance(image, dict):
        return None
    url = image.get(kind) or image.get("original") or image.get("medium")
    return str(url) if url else None


def _tv_country(show: dict) -> tuple[str | None, str | None]:
    for key in ("network", "webChannel"):
        obj = show.get(key) or {}
        if not isinstance(obj, dict):
            continue
        country = obj.get("country") or {}
        if isinstance(country, dict):
            return (str(country.get("name")) if country.get("name") else None,
                    str(country.get("code")) if country.get("code") else None)
    return (None, None)


def _year(date_str: str | None) -> int | None:
    if not date_str or len(date_str) < 4:
        return None
    try:
        return int(date_str[:4])
    except ValueError:
        return None


def _imdb_numeric(imdb_id: str | None) -> int | None:
    if not imdb_id:
        return None
    m = re.search(r"(\d+)", str(imdb_id))
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def normalize_imdb_item(item: dict) -> dict:
    if not isinstance(item, dict):
        return {}
    imdb_id = str(item.get("id") or "")
    num_id = _imdb_numeric(imdb_id) or 0
    qid = str(item.get("qid") or item.get("q") or "")
    media_type = "tv" if "tv" in qid.lower() or "series" in qid.lower() else "movie"
    title = item.get("l") or item.get("title") or ""
    year = item.get("y")
    date_str = f"{year}-01-01" if isinstance(year, int) else (item.get("yr") or "")
    img = item.get("i") or {}
    image_url = img.get("imageUrl") if isinstance(img, dict) else None
    stars = item.get("s") or ""
    overview = f"Cast: {stars}" if stars else ""
    return {
        "id": num_id,
        "imdb_id": imdb_id,
        "name": title,
        "title": title,
        "original_name": title,
        "original_title": title,
        "media_type": media_type,
        "overview": overview,
        "poster_path": image_url,
        "backdrop_path": image_url,
        "vote_average": 0.0,
        "vote_count": 0,
        "popularity": float(item.get("rank") or 0),
        "first_air_date": date_str if media_type == "tv" else "",
        "release_date": date_str if media_type == "movie" else "",
        "genre_ids": [],
        "genres": [],
        "credits": {"cast": [{"name": n.strip()} for n in stars.split(",") if n.strip()][:8], "crew": []},
        "videos": {"results": []},
        "watch/providers": {"results": {}},
        "production_countries": [],
        "_source": "imdb",
        "_qid": qid,
    }


def _omdb_imdb_id(value: str | None) -> str | None:
    text = str(value or "").strip()
    if re.fullmatch(r"tt\d{5,}", text):
        return text
    return None


def _omdb_date(value: str | None) -> str:
    text = str(value or "").strip()
    if not text or text == "N/A":
        return ""
    for fmt in ("%d %b %Y", "%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return ""


def _omdb_list(value: str | None) -> list[str]:
    text = str(value or "").strip()
    if not text or text == "N/A":
        return []
    return [part.strip() for part in text.split(",") if part.strip() and part.strip() != "N/A"]


def _omdb_int(value: str | None) -> int:
    digits = re.sub(r"[^\d]", "", str(value or ""))
    return int(digits) if digits else 0


def _omdb_float(value: str | None) -> float:
    try:
        return float(str(value or "0").replace(",", "."))
    except ValueError:
        return 0.0


def _omdb_poster(value: str | None) -> str | None:
    text = str(value or "").strip()
    return text if text.startswith(("http://", "https://")) else None


def normalize_omdb_search(entry: dict) -> dict:
    if not isinstance(entry, dict):
        return {}
    imdb_id = str(entry.get("imdbID") or "")
    title = str(entry.get("Title") or "")
    year = _year(str(entry.get("Year") or ""))
    kind = "tv" if str(entry.get("Type") or "").lower() in {"series", "episode"} else "movie"
    date_str = f"{year}-01-01" if year else ""
    return {
        "id": _imdb_numeric(imdb_id) or 0,
        "imdb_id": imdb_id,
        "name": title,
        "title": title,
        "original_name": title,
        "original_title": title,
        "media_type": kind,
        "overview": "",
        "poster_path": _omdb_poster(entry.get("Poster")),
        "backdrop_path": None,
        "vote_average": 0.0,
        "vote_count": 0,
        "popularity": 0.0,
        "first_air_date": date_str if kind == "tv" else "",
        "release_date": date_str if kind == "movie" else "",
        "genre_ids": [],
        "genres": [],
        "credits": {"cast": [], "crew": []},
        "videos": {"results": []},
        "watch/providers": {"results": {}},
        "production_countries": [],
        "_source": "omdb",
    }


def normalize_omdb_detail(data: dict) -> dict:
    if not isinstance(data, dict) or not data.get("imdbID"):
        return {}
    imdb_id = str(data.get("imdbID") or "")
    title = str(data.get("Title") or "")
    kind = "tv" if str(data.get("Type") or "").lower() in {"series", "episode"} else "movie"
    released = _omdb_date(data.get("Released")) or _omdb_date(data.get("Year"))
    genres = [{"name": name} for name in _omdb_list(data.get("Genre"))]
    countries = [{"name": name} for name in _omdb_list(data.get("Country"))]
    cast = [{"name": name} for name in _omdb_list(data.get("Actors"))]
    crew = [{"name": name, "job": "Director"} for name in _omdb_list(data.get("Director"))]
    crew += [{"name": name, "job": "Writer"} for name in _omdb_list(data.get("Writer"))]
    seasons = _omdb_int(data.get("totalSeasons"))
    return {
        "id": _imdb_numeric(imdb_id) or 0,
        "imdb_id": imdb_id,
        "name": title,
        "title": title,
        "original_name": title,
        "original_title": title,
        "media_type": kind,
        "overview": str(data.get("Plot") or "").replace("N/A", ""),
        "poster_path": _omdb_poster(data.get("Poster")),
        "backdrop_path": None,
        "vote_average": _omdb_float(data.get("imdbRating")),
        "vote_count": _omdb_int(data.get("imdbVotes")),
        "popularity": 0.0,
        "runtime": _omdb_int(data.get("Runtime")),
        "genres": genres,
        "production_countries": countries,
        "credits": {"cast": cast, "crew": crew},
        "videos": {"results": []},
        "watch/providers": {"results": {}},
        "official_site": f"https://www.imdb.com/title/{imdb_id}/",
        "first_air_date": released if kind == "tv" else "",
        "release_date": released,
        "status": str(data.get("Released") or "") if kind == "movie" else str(data.get("totalSeasons") or ""),
        "number_of_seasons": seasons if kind == "tv" else None,
        "number_of_episodes": None,
        "_source": "omdb",
    }


def _merge_items(*groups: list[dict]) -> list[dict]:
    seen: set[str] = set()
    result: list[dict] = []
    for group in groups:
        for item in group or []:
            if not isinstance(item, dict):
                continue
            key = str(item.get("imdb_id") or item.get("id") or "")
            if not key or key in seen:
                continue
            seen.add(key)
            result.append(item)
    return result


def normalize_show(show: dict | None) -> dict:
    if not isinstance(show, dict):
        return {}
    premiered = show.get("premiered") or show.get("ended") or ""
    genres = [g for g in (show.get("genres") or []) if isinstance(g, str)]
    rating = show.get("rating") or {}
    average = 0.0
    if isinstance(rating, dict):
        try:
            average = float(rating.get("average") or 0)
        except (TypeError, ValueError):
            average = 0.0
    country_name, country_code = _tv_country(show)
    lang = (show.get("language") or "")
    externals = show.get("externals") or {}
    imdb_id = externals.get("imdb") if isinstance(externals, dict) else None
    return {
        "id": int(show.get("id") or 0),
        "imdb_id": imdb_id,
        "name": show.get("name") or "",
        "title": show.get("name") or "",
        "original_name": show.get("name") or "",
        "original_title": show.get("name") or "",
        "media_type": "tv",
        "overview": _strip_html(show.get("summary")),
        "poster_path": _tv_image(show, "medium") or _tv_image(show, "original"),
        "backdrop_path": _tv_image(show, "original") or _tv_image(show, "medium"),
        "vote_average": average,
        "vote_count": 0,
        "popularity": float(show.get("weight") or 0),
        "first_air_date": premiered,
        "release_date": premiered,
        "genre_ids": [],
        "genres": [{"name": g} for g in genres],
        "original_language": lang.lower() if lang else None,
        "status": show.get("status") or "",
        "runtime": show.get("averageRuntime") or show.get("runtime"),
        "official_site": show.get("officialSite"),
        "network_country": country_name,
        "network_country_code": country_code,
        "_tvmaze_type": show.get("type") or "",
        "_tvmaze_url": show.get("url") or "",
        "_source": "tvmaze",
        "videos": {"results": []},
        "watch/providers": {"results": {}},
        "credits": {"cast": [], "crew": []},
        "production_countries": ([{"name": country_name}] if country_name else []),
    }


class TMDBClient:
    BASE_URL = "https://api.tvmaze.com"
    IMDB_SUGGEST_URL = "https://v3.sg.media-imdb.com/suggestion/x/{query}.json"
    IMAGE_URL = ""

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key or ""
        self.timeout = timeout if timeout is not None else settings.request_timeout
        self.max_retries = max_retries if max_retries is not None else settings.max_retries
        self._client = client
        self._owns_client = client is None
        self._shows_cache: list[dict] | None = None
        self._shows_cache_pages = 0
        self._item_cache: dict[tuple[str, int], dict] = {}

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={"Accept": "application/json", "User-Agent": "MovieUzBot/1.0"},
                follow_redirects=True,
            )
            self._owns_client = True
        return self._client

    async def close(self) -> None:
        if self._client is not None and self._owns_client and not self._client.is_closed:
            await self._client.aclose()
        self._client = None

    async def _request(self, url: str, params: dict[str, Any] | None = None, base: bool = True) -> Any:
        query = dict(params or {})
        if base and url.startswith("/"):
            url = self.BASE_URL + url
        client = await self._get_client()
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = await client.get(url, params=query)
                if response.status_code == 429:
                    if attempt < self.max_retries:
                        await asyncio.sleep(min(2 ** attempt, 8))
                        continue
                    raise TMDBError("API rate limit reached")
                if response.status_code == 404:
                    return {} if "/search" not in url else []
                if response.status_code >= 500 and attempt < self.max_retries:
                    await asyncio.sleep(0.5 * (2 ** attempt))
                    continue
                if not response.is_success:
                    raise TMDBError(f"API returned HTTP {response.status_code}")
                try:
                    return response.json()
                except ValueError as exc:
                    raise TMDBError("API returned invalid JSON") from exc
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    await asyncio.sleep(0.5 * (2 ** attempt))
                    continue
                raise TMDBError("API network error") from exc
            except TMDBError:
                raise
        raise TMDBError(str(last_error or "API request failed"))

    @property
    def omdb_enabled(self) -> bool:
        return bool(settings.omdb_api_key)

    async def _omdb_request(self, params: dict[str, Any]) -> dict:
        if not self.omdb_enabled:
            return {}
        query = dict(params)
        query["apikey"] = settings.omdb_api_key
        try:
            data = await self._request("https://www.omdbapi.com/", query, base=False)
        except TMDBError:
            return {}
        if not isinstance(data, dict) or str(data.get("Response")).lower() == "false":
            return {}
        return data

    async def omdb_search(
        self,
        query: str,
        media_type: str | None = None,
        page: int = 1,
        year: int | None = None,
    ) -> list[dict]:
        params: dict[str, Any] = {"s": query, "page": max(1, min(int(page), 100))}
        if media_type in {"movie", "series", "episode"}:
            params["type"] = media_type
        if year:
            params["y"] = year
        data = await self._omdb_request(params)
        results = data.get("Search") if isinstance(data, dict) else None
        items: list[dict] = []
        for entry in results or []:
            if not isinstance(entry, dict):
                continue
            normalized = normalize_omdb_search(entry)
            if normalized.get("id"):
                self._remember(normalized)
                items.append(normalized)
        return items

    async def omdb_details(self, imdb_id: str | None) -> dict:
        imdb = _omdb_imdb_id(imdb_id)
        if not imdb:
            return {}
        data = await self._omdb_request({"i": imdb, "plot": "full"})
        if not data:
            return {}
        detail = normalize_omdb_detail(data)
        if detail:
            self._remember(detail)
        return detail

    def image_url(self, path: str | None, size: str = "w500") -> str | None:
        if not path:
            return None
        if str(path).startswith(("http://", "https://")):
            return str(path)
        return None

    def _remember(self, item: dict) -> None:
        try:
            key = (str(item.get("media_type") or "movie"), int(item.get("id") or 0))
            if key[1] > 0:
                self._item_cache[key] = item
        except Exception:
            pass

    async def _imdb_suggest(self, query: str) -> list[dict]:
        q = re.sub(r"[^a-zA-Z0-9 ]+", " ", (query or "").strip().lower()).strip()
        q = re.sub(r"\s+", "_", q)
        if not q:
            return []
        url = self.IMDB_SUGGEST_URL.format(query=q[:60])
        try:
            data = await self._request(url, base=False)
        except TMDBError:
            return []
        items: list[dict] = []
        if isinstance(data, dict):
            for entry in data.get("d") or []:
                if not isinstance(entry, dict) or not entry.get("id", "").startswith("tt"):
                    continue
                normalized = normalize_imdb_item(entry)
                if normalized.get("id"):
                    self._remember(normalized)
                    items.append(normalized)
        return items

    async def _search_shows(self, query: str) -> list[dict]:
        data = await self._request("/search/shows", {"q": query})
        items: list[dict] = []
        if isinstance(data, list):
            for entry in data:
                if isinstance(entry, dict) and isinstance(entry.get("show"), dict):
                    show = normalize_show(entry["show"])
                    self._remember(show)
                    items.append(show)
        return items

    async def search_multi(self, query: str, language: str = "uz", page: int = 1) -> list[dict]:
        imdb_items = await self._imdb_suggest(query)
        omdb_items = await self.omdb_search(query, page=page)
        merged = _merge_items(imdb_items, omdb_items)
        if merged:
            return merged
        return await self._search_shows(query)

    async def search_movies(self, query: str, language: str = "uz", page: int = 1, year: int | None = None) -> list[dict]:
        results = await self._imdb_suggest(query)
        results = [r for r in results if r.get("media_type") == "movie"]
        if year:
            results = [r for r in results if _year(r.get("release_date")) == year]
        results = _merge_items(
            results, await self.omdb_search(query, media_type="movie", page=page, year=year)
        )
        if not results:
            results = await self._search_shows(query)
            if year:
                results = [r for r in results if _year(r.get("first_air_date")) == year]
        return results

    async def search_tv(self, query: str, language: str = "uz", page: int = 1, year: int | None = None) -> list[dict]:
        results = await self._imdb_suggest(query)
        tv = [r for r in results if r.get("media_type") == "tv"]
        if year:
            tv = [r for r in tv if _year(r.get("first_air_date")) == year]
        tv = _merge_items(
            tv, await self.omdb_search(query, media_type="series", page=page, year=year)
        )
        if not tv:
            tv = await self._search_shows(query)
            if year:
                tv = [r for r in tv if _year(r.get("first_air_date")) == year]
        return tv

    async def search_person(self, query: str, page: int = 1) -> list[dict]:
        data = await self._request("/search/people", {"q": query})
        people: list[dict] = []
        if isinstance(data, list):
            for entry in data:
                if not isinstance(entry, dict) or not isinstance(entry.get("person"), dict):
                    continue
                person = entry["person"]
                image = person.get("image") or {}
                people.append({
                    "id": int(person.get("id") or 0),
                    "name": person.get("name") or "",
                    "image": (image.get("medium") if isinstance(image, dict) else None),
                    "known_for": [],
                })
        return people

    async def _ensure_show_index(self, pages: int = 8) -> list[dict]:
        if self._shows_cache is not None and self._shows_cache_pages >= pages:
            return self._shows_cache
        items: list[dict] = []
        for page in range(pages):
            data = await self._request("/shows", {"page": page})
            if not isinstance(data, list) or not data:
                break
            for show in data:
                if isinstance(show, dict):
                    items.append(normalize_show(show))
        self._shows_cache = items
        self._shows_cache_pages = pages
        return items

    def _filter_shows(self, shows: list[dict], genre_names: list[str] | None = None, country: str | None = None, original_language: str | None = None, year: int | None = None, sort_by: str = "popularity.desc") -> list[dict]:
        result = list(shows)
        if genre_names:
            wanted = {g.lower() for g in genre_names}
            def has_genre(s: dict) -> bool:
                gset = {g.get("name", "").lower() for g in s.get("genres", []) if isinstance(g, dict)}
                if wanted.intersection(gset):
                    return True
                if "animation" in wanted and (s.get("_tvmaze_type") == "Animation" or "anime" in gset):
                    return True
                return False
            result = [s for s in result if has_genre(s)]
        if country:
            cc = country.upper()
            result = [s for s in result if (s.get("network_country_code") or "").upper() == cc]
        if original_language:
            ol = original_language.lower()
            lang_name = _LANG_NAME.get(ol, ol)
            result = [s for s in result if (s.get("original_language") or "").lower() in {ol, lang_name}]
        if year:
            result = [s for s in result if _year(s.get("first_air_date")) == year]
        if sort_by.startswith("vote_average"):
            result.sort(key=lambda x: float(x.get("vote_average") or 0), reverse=True)
        elif sort_by.startswith("first_air_date") or sort_by.startswith("primary_release_date"):
            result.sort(key=lambda x: str(x.get("first_air_date") or ""), reverse=True)
        else:
            result.sort(key=lambda x: float(x.get("popularity") or 0), reverse=True)
        return result

    @staticmethod
    def _page_result(items: list[dict], page: int, per_page: int = 20) -> dict:
        total_pages = max(1, (len(items) + per_page - 1) // per_page)
        page = max(1, min(page, total_pages))
        start = (page - 1) * per_page
        return {"results": items[start:start + per_page], "total_pages": total_pages, "page": page}

    async def discover_movies(self, page: int = 1, language: str = "uz", sort_by: str = "popularity.desc", genre_ids: list[int] | None = None, country: str | None = None, original_language: str | None = None, year: int | None = None, release_gte: str | None = None, release_lte: str | None = None, vote_count_gte: int | None = None) -> dict:
        return await self.discover_tv(page=page, language=language, sort_by=sort_by, genre_ids=genre_ids, country=country, original_language=original_language, year=year, vote_count_gte=vote_count_gte)

    async def discover_tv(self, page: int = 1, language: str = "uz", sort_by: str = "popularity.desc", genre_ids: list[int] | None = None, country: str | None = None, original_language: str | None = None, year: int | None = None, vote_count_gte: int | None = None) -> dict:
        genre_names = [_GENRE_MAP[g] for g in (genre_ids or []) if g in _GENRE_MAP]
        index = await self._ensure_show_index(pages=10)
        filtered = self._filter_shows(index, genre_names=genre_names or None, country=country, original_language=original_language, year=year, sort_by=sort_by)
        if vote_count_gte:
            filtered = [s for s in filtered if float(s.get("vote_average") or 0) > 0]
        return self._page_result(filtered, page)

    async def popular_movies(self, page: int = 1, language: str = "uz", region: str | None = None) -> dict:
        return await self.popular_tv(page, language)

    async def top_rated_movies(self, page: int = 1, language: str = "uz") -> dict:
        return await self.top_rated_tv(page, language)

    async def now_playing(self, page: int = 1, language: str = "uz") -> dict:
        data = await self._request("/schedule", {"country": "US", "date": date.today().isoformat()})
        shows: list[dict] = []
        seen: set[int] = set()
        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    continue
                show = (item.get("_embedded") or {}).get("show") if isinstance(item.get("_embedded"), dict) else item.get("show")
                if isinstance(show, dict):
                    sid = int(show.get("id") or 0)
                    if sid and sid not in seen:
                        seen.add(sid)
                        shows.append(normalize_show(show))
        if not shows:
            return await self.popular_tv(page, language)
        return self._page_result(shows, page)

    async def upcoming_movies(self, page: int = 1, language: str = "uz") -> dict:
        return {"results": [], "total_pages": 1, "page": 1}

    async def popular_tv(self, page: int = 1, language: str = "uz") -> dict:
        index = await self._ensure_show_index(pages=10)
        shows = sorted(index, key=lambda x: float(x.get("popularity") or 0), reverse=True)
        return self._page_result(shows, page)

    async def top_rated_tv(self, page: int = 1, language: str = "uz") -> dict:
        index = await self._ensure_show_index(pages=10)
        shows = sorted([s for s in index if float(s.get("vote_average") or 0) > 0], key=lambda x: float(x.get("vote_average") or 0), reverse=True)
        return self._page_result(shows, page)

    async def trending(self, media_type: str = "movie", page: int = 1) -> dict:
        return await self.popular_tv(page)

    async def details(self, media_type: str, item_id: int, language: str = "uz", append: bool = True) -> dict:
        kind = "tv" if media_type == "tv" else "movie"
        item_key = int(item_id)
        cached = (
            self._item_cache.get((kind, item_key))
            or self._item_cache.get(("movie" if kind == "tv" else "tv", item_key))
        )
        if cached and str(cached.get("_source") or "").lower() in {"imdb", "omdb"}:
            omdb_detail = await self.omdb_details(cached.get("imdb_id"))
            if omdb_detail:
                return omdb_detail
        # try tvmaze first (for tv/show ids)
        try:
            params = {"embed[]": ["cast", "crew", "seasons", "episodes", "images"]} if append else {}
            data = await self._request(f"/shows/{item_id}", params)
            if isinstance(data, dict) and data.get("id"):
                show = normalize_show(data)
                embedded = data.get("_embedded") or {} if isinstance(data.get("_embedded"), dict) else {}
                cast_entries = embedded.get("cast") or []
                crew_entries = embedded.get("crew") or []
                cast = []
                for entry in cast_entries if isinstance(cast_entries, list) else []:
                    if not isinstance(entry, dict):
                        continue
                    person = entry.get("person") or {}
                    character = entry.get("character") or {}
                    img = (person.get("image") or {}) if isinstance(person, dict) else {}
                    cast.append({
                        "id": (person.get("id") if isinstance(person, dict) else None),
                        "name": (person.get("name") if isinstance(person, dict) else ""),
                        "character": (character.get("name") if isinstance(character, dict) else ""),
                        "profile_path": img.get("medium") if isinstance(img, dict) else None,
                    })
                crew = []
                for entry in crew_entries if isinstance(crew_entries, list) else []:
                    if not isinstance(entry, dict):
                        continue
                    person = entry.get("person") or {}
                    img = (person.get("image") or {}) if isinstance(person, dict) else {}
                    crew.append({
                        "id": (person.get("id") if isinstance(person, dict) else None),
                        "name": (person.get("name") if isinstance(person, dict) else ""),
                        "job": entry.get("type") or "",
                        "profile_path": img.get("medium") if isinstance(img, dict) else None,
                    })
                seasons = embedded.get("seasons") or []
                episodes = embedded.get("episodes") or []
                show["credits"] = {"cast": cast, "crew": crew}
                show["genres"] = [{"name": g} for g in (data.get("genres") or []) if isinstance(g, str)]
                if isinstance(seasons, list):
                    show["number_of_seasons"] = len(seasons)
                if isinstance(episodes, list):
                    show["number_of_episodes"] = len(episodes)
                images = embedded.get("images") or []
                if isinstance(images, list):
                    for img in images:
                        if isinstance(img, dict) and img.get("type") == "background":
                            resolutions = img.get("resolutions") or {}
                            orig = (resolutions.get("original") or {}) if isinstance(resolutions, dict) else {}
                            if isinstance(orig, dict) and orig.get("url"):
                                show["backdrop_path"] = orig.get("url")
                                break
                self._remember(show)
                return show
        except TMDBError:
            pass
        # fallback: imdb-sourced cached item or minimal
        if cached:
            detail = dict(cached)
            imdb_id = detail.get("imdb_id") or f"tt{item_id}"
            if not detail.get("overview"):
                detail["overview"] = ""
            detail.setdefault("credits", {"cast": [], "crew": []})
            detail.setdefault("videos", {"results": []})
            detail.setdefault("watch/providers", {"results": {}})
            detail.setdefault("production_countries", [])
            detail["official_site"] = detail.get("official_site") or f"https://www.imdb.com/title/{imdb_id}/"
            return detail
        # last resort minimal card
        imdb_id = f"tt{item_id}"
        return {
            "id": int(item_id),
            "imdb_id": imdb_id,
            "name": "", "title": "",
            "media_type": kind,
            "overview": "",
            "poster_path": None,
            "backdrop_path": None,
            "vote_average": 0,
            "vote_count": 0,
            "genres": [],
            "credits": {"cast": [], "crew": []},
            "videos": {"results": []},
            "watch/providers": {"results": {}},
            "production_countries": [],
            "official_site": f"https://www.imdb.com/title/{imdb_id}/",
            "first_air_date": "",
            "release_date": "",
        }

    async def credits(self, media_type: str, item_id: int, language: str = "uz") -> dict:
        details = await self.details(media_type, item_id, language, append=True)
        return details.get("credits") or {"cast": [], "crew": []}

    async def videos(self, media_type: str, item_id: int, language: str = "uz") -> list[dict]:
        return []

    async def watch_providers(self, media_type: str, item_id: int) -> dict:
        return {"results": {}}

    async def recommendations(self, media_type: str, item_id: int, language: str = "uz", page: int = 1) -> list[dict]:
        return []

    async def similar(self, media_type: str, item_id: int, language: str = "uz", page: int = 1) -> list[dict]:
        return []

    async def person(self, person_id: int, language: str = "uz") -> dict:
        try:
            data = await self._request(f"/people/{person_id}", {"embed": "castcredits"})
        except TMDBError:
            return {}
        if not isinstance(data, dict) or not data:
            return {}
        image = data.get("image") or {}
        return {
            "id": int(data.get("id") or 0),
            "name": data.get("name") or "",
            "biography": "",
            "profile_path": image.get("medium") if isinstance(image, dict) else None,
            "birthday": data.get("birthday"),
            "place_of_birth": data.get("country", {}).get("name") if isinstance(data.get("country"), dict) else None,
            "known_for": {"results": [], "cast": []},
        }

    async def genres(self, media_type: str = "movie", language: str = "uz") -> list[dict]:
        names = sorted(set(_GENRE_MAP.values()))
        return [{"id": i + 1, "name": name} for i, name in enumerate(names)]

    async def random_movie(self, genre_id: int | None = None, language: str = "uz") -> dict | None:
        if genre_id and genre_id in _GENRE_MAP:
            try:
                data = await self.discover_tv(genre_ids=[genre_id], page=random.randint(1, 5))
                results = [r for r in data.get("results", []) if isinstance(r, dict)]
                if results:
                    return random.choice(results)
            except TMDBError:
                pass
        # try a popular-ish show page
        try:
            index = await self._ensure_show_index(pages=10)
            if index:
                return random.choice(index[:200] if len(index) > 200 else index)
        except TMDBError:
            pass
        return None


tmdb = TMDBClient()
