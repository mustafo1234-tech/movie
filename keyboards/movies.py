from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from utils.i18n import t

GENRES: list[tuple[int, str]] = [
    (28, "action"),
    (12, "adventure"),
    (16, "animation"),
    (35, "comedy"),
    (80, "crime"),
    (99, "documentary"),
    (18, "drama"),
    (10751, "family"),
    (14, "fantasy"),
    (36, "history"),
    (27, "horror"),
    (10402, "music"),
    (9648, "mystery"),
    (10749, "romance"),
    (878, "science_fiction"),
    (53, "thriller"),
    (10752, "war"),
    (37, "western"),
]

COUNTRIES: list[tuple[str, str, str]] = [
    ("uz", "UZ", "uz"),
    ("us", "US", "en"),
    ("kr", "KR", "ko"),
    ("in", "IN", "hi"),
    ("tr", "TR", "tr"),
    ("jp", "JP", "ja"),
    ("cn", "CN", "zh"),
    ("gb", "GB", "en"),
    ("ru", "RU", "ru"),
    ("fr", "FR", "fr"),
]


def _inline(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def detail_keyboard(
    lang: str,
    media_type: str,
    item_id: int,
    favorite: bool = False,
    watched: bool = False,
    trailer_url: str | None = None,
    watch_url: str | None = None,
    backdrop: bool = False,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [
            _inline(t(lang, "btn.remove_favorite" if favorite else "btn.add_favorite"), f"fav:{media_type}:{item_id}"),
            _inline(t(lang, "btn.unwatched" if watched else "btn.mark_watched"), f"wat:{media_type}:{item_id}"),
        ],
        [
            _inline(t(lang, "btn.cast"), f"cast:{media_type}:{item_id}:1"),
            _inline(t(lang, "btn.similar"), f"sim:{media_type}:{item_id}:1"),
        ],
        [
            _inline(t(lang, "btn.recommend"), f"rec:{media_type}:{item_id}:1"),
            _inline(t(lang, "btn.random"), "rnd:0"),
        ],
    ]
    links: list[InlineKeyboardButton] = []
    if trailer_url:
        links.append(InlineKeyboardButton(text=t(lang, "btn.trailer"), url=trailer_url))
    if watch_url:
        links.append(InlineKeyboardButton(text=t(lang, "btn.watch"), url=watch_url))
    if links:
        rows.append(links)
    last_row: list[InlineKeyboardButton] = []
    if backdrop:
        last_row.append(_inline(t(lang, "btn.backdrop"), f"bd:{media_type}:{item_id}"))
    last_row.append(_inline(t(lang, "btn.main_menu"), "home"))
    rows.append(last_row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def items_keyboard(
    lang: str,
    token: str,
    page: int,
    pages: int,
    count: int,
    prefix: str = "pg",
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    numbers = [_inline(str(index + 1), f"itm:{token}:{index}") for index in range(count)]
    for start in range(0, len(numbers), 5):
        rows.append(numbers[start : start + 5])
    navigation: list[InlineKeyboardButton] = []
    if page > 1:
        navigation.append(_inline(t(lang, "btn.prev"), f"{prefix}:{token}:{page - 1}"))
    if page < pages:
        navigation.append(_inline(t(lang, "btn.next"), f"{prefix}:{token}:{page + 1}"))
    if navigation:
        rows.append(navigation)
    rows.append(
        [
            _inline(t(lang, "btn.new_search"), "newsearch"),
            _inline(t(lang, "btn.main_menu"), "home"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def list_keyboard(
    lang: str, token: str, page: int, pages: int, prefix: str = "pg"
) -> InlineKeyboardMarkup:
    return items_keyboard(lang, token, page, pages, 0, prefix)


def catalog_keyboard(
    lang: str,
    token: str,
    catalog_key: str,
    local_page: int,
    local_pages: int,
    api_page: int,
    api_pages: int,
    count: int,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    numbers = [
        _inline(str(index + 1), f"itm:{token}:{index}")
        for index in range((local_page - 1) * 5, min(local_page * 5, count))
    ]
    for start in range(0, len(numbers), 5):
        rows.append(numbers[start : start + 5])
    navigation: list[InlineKeyboardButton] = []
    if local_page > 1:
        navigation.append(_inline(t(lang, "btn.prev"), f"lst:{token}:{local_page - 1}"))
    if local_page < local_pages:
        navigation.append(_inline(t(lang, "btn.next"), f"lst:{token}:{local_page + 1}"))
    if local_page == local_pages and api_page < api_pages:
        navigation.append(_inline(t(lang, "btn.next"), f"catnext:{catalog_key}:{api_page + 1}"))
    if local_page == 1 and api_page > 1:
        navigation.append(_inline(t(lang, "btn.prev"), f"catprev:{catalog_key}:{api_page - 1}"))
    if navigation:
        rows.append(navigation)
    rows.append(
        [
            _inline(t(lang, "btn.new_search"), "newsearch"),
            _inline(t(lang, "btn.main_menu"), "home"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def genres_keyboard(lang: str, selected: set[int] | None = None) -> InlineKeyboardMarkup:
    selected = selected or set()
    rows: list[list[InlineKeyboardButton]] = []
    for index in range(0, len(GENRES), 3):
        row: list[InlineKeyboardButton] = []
        for genre_id, key in GENRES[index : index + 3]:
            mark = "✅ " if genre_id in selected else ""
            row.append(_inline(f"{mark}{t(lang, f'genre.{key}')}", f"gen:{genre_id}"))
        rows.append(row)
    rows.append([_inline(t(lang, "btn.confirm"), "gdone")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def countries_keyboard(lang: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for index in range(0, len(COUNTRIES), 2):
        rows.append(
            [
                _inline(t(lang, f"country.{key}"), f"ctry:{key}")
                for key, _, _ in COUNTRIES[index : index + 2]
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def random_keyboard(lang: str) -> InlineKeyboardMarkup:
    rows = [
        [_inline(t(lang, "btn.random"), "rnd:0"), _inline(t(lang, "btn.random_by_genre"), "rndgenre")],
        [_inline(t(lang, "btn.main_menu"), "home")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def person_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[_inline(t(lang, "btn.main_menu"), "home")]]
    )
