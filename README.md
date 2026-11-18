# MovieUz Bot

Professional, bepul va ochiq Telegram bot. Serial, anime va TV shoularni [TVmaze](https://www.tvmaze.com/api) (bepul, public API) katalogidan qidiradi; tafsilot, tavsiya, sevimlilar va ko‘rilganlar ro‘yxatlarini ta’minlaydi.

## Imkoniyatlar

- Qidiruv (nomi, original nomi, yil, aktyor)
- Aqlli qidiruv: xato yozishga chidamli, o‘xshashlik bo‘yicha saralash, takrorlarsiz natijalar
- To‘liq karta: poster, fon, aktyorlar va mavjud tafsilotlar
- Katalog bo‘limlari: mashhur, top reyting, yangi/efirdagi, seriallar, anime/animatsiya
- Janrlar (ko‘p tanlov), davlatlar bo‘yicha filtr
- Sevimlilar, ko‘rilganlar, shaxsiy profil statistikasi
- Tavsiya va tasodifiy tanlov
- Uzbek / Russian tillari (database’da saqlanadi)
- Admin panel: statistika, foydalanuvchilar, broadcast, sozlamalar, holat
- Redis cache (ixtiyoriy), retry/timeout, strukturali logging

Pullik obuna, to‘lov tizimlari va noqonuniy yuklab olish funksiyalari yo‘q.

## 1. Kerakli sozlamalar

- `BOT_TOKEN` — https://t.me/BotFather dan olingan token.
- `ADMIN_IDS` — admin Telegram ID’lari, vergul bilan: `123456789,987654321`.
- TVmaze API ochiq va bepul, API key talab qilinmaydi.

Kalitlarni kodga yozmang. Faqat `.env` faylida saqlang. `.env` `.gitignore` ga kiritilgan.

## 2. .env sozlash

```bash
cp .env.example .env
```

`.env` namunasi:

```env
BOT_TOKEN=your_bot_token_here
ADMIN_IDS=123456789
DATABASE_URL=sqlite+aiosqlite:///./movieuz.db
REDIS_URL=
```

Redis ixtiyoriy: `REDIS_URL=redis://localhost:6379/0` bo‘lsa ishlatiladi, bo‘lmasa xotira cache ishlatiladi.

## 3. Kutubxonalar

```bash
python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows PowerShell
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Python 3.11+ talab qilinadi.

## 4. Database

Local development (SQLite) — avtomatik yaratiladi:

```bash
python -c "import asyncio; from database.engine import init_db; asyncio.run(init_db())"
```

Alembic migration bilan:

```bash
alembic upgrade head
```

Production (PostgreSQL) — `.env` da:

```env
DATABASE_URL=postgresql+asyncpg://movieuz:movieuz@localhost:5432/movieuz
```

## 5. Botni ishga tushirish

```bash
python bot.py
```

Docker bilan:

```bash
docker compose up -d --build
```

## 6. Testlar

```bash
pytest -q
```

## Eslatma

TVmaze asosan TV show/serial ma’lumotlarini beradi (filmlar yo‘q). Ba’zi funksiyalar (treyler, tomosha havolalari, o‘xshash/tavsiyalar, to‘liq reytinglar) manba imkoniyatiga qarab cheklangan bo‘lishi mumkin. Bot faqat API’da mavjud ma’lumotlarni ko‘rsatadi.

TVmaze API: https://www.tvmaze.com/api
