# TELGRAM BOT: "Guessin Game"
import asyncio
import calendar
import logging
import os
import random
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import psycopg2
import psycopg2.extras

from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

load_dotenv()  # .env faylidagi o'zgaruvchilarni yuklaydi

logging.basicConfig(level=logging.INFO)

# Token endi kodda yo'q — u faqat .env faylidan yoki server sozlamalaridan o'qiladi
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN topilmadi! Loyiha papkasida .env fayl yarating va ichiga "
        "BOT_TOKEN=sizning_tokeningiz deb yozing (namuna uchun .env.example ga qarang)."
    )

DUEL_RANGE = 100  # Duel rejimida hamma doim 1 dan shu songacha o'ynaydi (adolatli matchmaking uchun)

# Umr hisoblagich: server (Render) UTC da ishlaydi, shuning uchun vaqt aniq Toshkent bo'yicha olinadi
try:
    TZ = ZoneInfo("Asia/Tashkent")
except Exception:  # tzdata o'rnatilmagan bo'lsa (Toshkentda yozgi vaqt yo'q, doim UTC+5)
    TZ = timezone(timedelta(hours=5))
AGE_MIN_YEAR = 1920  # tanlash mumkin bo'lgan eng eski yil
AGE_YEARS_PER_PAGE = 12

ADMIN_ID = 8612968177  # Faqat shu Telegram ID /admin_stats buyrug'ini ishlata oladi

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL topilmadi! Render'ning Environment bo'limiga Neon'dan "
        "olingan connection string'ni DATABASE_URL nomi bilan qo'shing."
    )

TEXTS = {
    "uz": {
        "choose_lang": "🎮 Xush kelibsiz! Tilni tanlang:",
        "lang_ok": "🇺🇿 O'zbek tili tanlandi!",
        "menu_title": "🎮 Bosh menyu",
        "btn_start": "1️⃣ O'yinni boshlash",
        "btn_duel": "2️⃣ ⚔️ Duel",
        "btn_stats": "3️⃣ Statistikam",
        "btn_rating": "4️⃣ Reyting",
        "btn_lang": "5️⃣ Tilni o'zgartirish",
        "btn_age": "6️⃣ Umr hisoblagich",
        "soon": "⏳ Bu qism hali tayyor emas. Tez orada qo'shamiz!",
        "age_prompt": "🎂 Umr hisoblagich\n\nTug'ilgan sanangizni tugmalar orqali tanlang: avval yil, keyin oy, keyin kun.\nNamuna: 01.07.2011\n\n📅 Yilni tanlang:",
        "age_pick_month": "🎂 Yil: {year}\n\n📅 Oyni tanlang:",
        "age_pick_day": "🎂 Yil: {year}, oy: {month}\n\n📅 Kunni tanlang:",
        "age_months": ["Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun", "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"],
        "age_result": "🎂 Tug'ilgan sana: {birth}\n🕒 Hozir: {now}\n\n📅 Aniq yosh: {years} yil, {months} oy, {days} kun\n\n• Oy: {total_months} oy (+ {extra_days} kun)\n• Kun: {total_days} kun\n• Hafta: {total_weeks} hafta (+ {extra_week_days} kun)\n• Soat: {total_hours} soat\n• Daqiqa: {total_minutes} daqiqa\n• Soniya: {total_seconds} soniya\n\n{next}\n\n(Tug'ilgan vaqt 00:00 deb olindi, kabisa yillari hisobga olingan.)",
        "age_next": "🎁 Keyingi tug'ilgan kunga: {days} kun",
        "age_birthday_today": "🎉 Bugun tug'ilgan kuningiz muborak bo'lsin!",
        "age_future": "❌ Tug'ilgan sana kelajakda bo'la olmaydi.",
        "age_btn_newer": "⬅️ Yangiroq",
        "age_btn_older": "Eskiroq ➡️",
        "age_btn_year": "⬅️ Yilni o'zgartirish",
        "age_btn_month": "⬅️ Oyni o'zgartirish",
        "age_again": "🔄 Boshqa sana",
        "difficulty_title": "🎯 Qiyinchilik darajasini tanlang:",
        "btn_easy": "🟢 Easy (1-50)",
        "btn_medium": "🟡 Medium (1-100)",
        "btn_hard": "🔴 Hard (1-500)",
        "think": "🎯 Men 1 dan {max_number} gacha son o'yladim! Taxmin qiling 👇",
        "not_number": "❌ Iltimos, butun son kiriting!",
        "higher": "⬆️ Kattaroq son!",
        "lower": "⬇️ Kichikroq son!",
        "correct": "🎉 To'g'ri! {attempts} ta urinishda topdingiz!",
        "btn_menu": "🏠 Bosh menyu",
        "duel_searching": "🔍 Raqib qidirilmoqda... Iltimos kuting.",
        "btn_cancel": "❌ Bekor qilish",
        "duel_cancelled": "❌ Qidiruv bekor qilindi.",
        "duel_found": "⚔️ Raqib topildi: {opponent}!\n🎯 Ikkalangiz ham 1 dan {max_number} gacha bo'lgan bir xil sonni taxmin qilasiz. Kim birinchi topsa — g'olib!",
        "duel_win": "🏆 Siz g'olib bo'ldingiz! Sonni {attempts} ta urinishda topdingiz!",
        "duel_lose": "😔 Siz yutqazdingiz. Raqibingiz {opponent} sonni birinchi topdi.\n✅ To'g'ri son: {secret}",
        "duel_already_finished": "⚠️ Bu duel allaqachon tugagan.",
        "stats_title": "📊 Sizning statistikangiz",
        "stats_games": "🎮 O'ynagan o'yinlar: {games}",
        "stats_best": "🏅 Eng yaxshi natija: {best} urinish",
        "stats_avg": "📈 O'rtacha urinish: {avg}",
        "stats_duel": "⚔️ Duel: {wins} g'alaba / {losses} mag'lubiyat",
        "stats_empty": "📊 Sizda hali statistika yo'q. Avval o'ynang!",
        "rating_title": "🏆 TOP o'yinchilar (Duel g'alabalari bo'yicha):\n",
        "rating_row": "{rank}. {name} — {wins} g'alaba ({losses} mag'lubiyat)",
        "rating_empty": "🏆 Hali hech kim duel o'ynamagan. Birinchi bo'ling!",
    },
    "en": {
        "choose_lang": "🎮 Welcome! Choose your language:",
        "lang_ok": "🇬🇧 English selected!",
        "menu_title": "🎮 Main menu",
        "btn_start": "1️⃣ Start Game",
        "btn_duel": "2️⃣ ⚔️ Duel",
        "btn_stats": "3️⃣ My Statistics",
        "btn_rating": "4️⃣ Leaderboard",
        "btn_lang": "5️⃣ Change Language",
        "btn_age": "6️⃣ Age Calculator",
        "soon": "⏳ This part is not ready yet. We will add it soon!",
        "age_prompt": "🎂 Age Calculator\n\nPick your birth date with the buttons: year first, then month, then day.\nExample: 01.07.2011\n\n📅 Choose the year:",
        "age_pick_month": "🎂 Year: {year}\n\n📅 Choose the month:",
        "age_pick_day": "🎂 Year: {year}, month: {month}\n\n📅 Choose the day:",
        "age_months": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
        "age_result": "🎂 Birth date: {birth}\n🕒 Now: {now}\n\n📅 Exact age: {years} years, {months} months, {days} days\n\n• Months: {total_months} months (+ {extra_days} days)\n• Days: {total_days} days\n• Weeks: {total_weeks} weeks (+ {extra_week_days} days)\n• Hours: {total_hours} hours\n• Minutes: {total_minutes} minutes\n• Seconds: {total_seconds} seconds\n\n{next}\n\n(Birth time is taken as 00:00, leap years are included.)",
        "age_next": "🎁 Next birthday in: {days} days",
        "age_birthday_today": "🎉 Happy birthday today!",
        "age_future": "❌ Birth date cannot be in the future.",
        "age_btn_newer": "⬅️ Newer",
        "age_btn_older": "Older ➡️",
        "age_btn_year": "⬅️ Change year",
        "age_btn_month": "⬅️ Change month",
        "age_again": "🔄 Another date",
        "difficulty_title": "🎯 Choose difficulty:",
        "btn_easy": "🟢 Easy (1-50)",
        "btn_medium": "🟡 Medium (1-100)",
        "btn_hard": "🔴 Hard (1-500)",
        "think": "🎯 I chose a number between 1 and {max_number}! Guess it 👇",
        "not_number": "❌ Please enter a whole number!",
        "higher": "⬆️ Try higher!",
        "lower": "⬇️ Try lower!",
        "correct": "🎉 Correct! You guessed it in {attempts} attempts!",
        "btn_menu": "🏠 Main menu",
        "duel_searching": "🔍 Searching for an opponent... Please wait.",
        "btn_cancel": "❌ Cancel",
        "duel_cancelled": "❌ Search cancelled.",
        "duel_found": "⚔️ Opponent found: {opponent}!\n🎯 You're both guessing the same number between 1 and {max_number}. Whoever guesses first wins!",
        "duel_win": "🏆 You won! You guessed it in {attempts} attempts!",
        "duel_lose": "😔 You lost. {opponent} guessed the number first.\n✅ Correct number was: {secret}",
        "duel_already_finished": "⚠️ This duel has already ended.",
        "stats_title": "📊 Your statistics",
        "stats_games": "🎮 Games played: {games}",
        "stats_best": "🏅 Best result: {best} attempts",
        "stats_avg": "📈 Average attempts: {avg}",
        "stats_duel": "⚔️ Duel: {wins} wins / {losses} losses",
        "stats_empty": "📊 You don't have any statistics yet. Play a game first!",
        "rating_title": "🏆 TOP players (by Duel wins):\n",
        "rating_row": "{rank}. {name} — {wins} wins ({losses} losses)",
        "rating_empty": "🏆 No one has played a duel yet. Be the first!",
    },
}


class GameStates(StatesGroup):
    choosing_language = State()
    main_menu = State()
    choosing_difficulty = State()
    guessing = State()
    duel_waiting = State()
    duel_guessing = State()


storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# --- Matchmaking uchun global holat ---
waiting_player: dict | None = None  # {"user_id", "chat_id", "name", "language"}
active_duels: dict[int, dict] = {}  # duel_id -> {"secret", "finished", "players": {user_id: {...}}}
next_duel_id = 1


# --- Statistika bazasi (Postgres / Neon) ---


def get_conn():
    return psycopg2.connect(DATABASE_URL, sslmode="require")


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            name TEXT NOT NULL,
            username TEXT,
            games_played INTEGER NOT NULL DEFAULT 0,
            total_attempts INTEGER NOT NULL DEFAULT 0,
            best_attempts INTEGER,
            duel_wins INTEGER NOT NULL DEFAULT 0,
            duel_losses INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    # Eski bazalarda username ustuni bo'lmasligi mumkin — bo'lmasa qo'shib qo'yamiz
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS username TEXT")
    conn.commit()
    cur.close()
    conn.close()


def _ensure_user(cur, user_id: int, name: str, username: str | None = None) -> None:
    cur.execute(
        "INSERT INTO users (user_id, name, username) VALUES (%s, %s, %s) "
        "ON CONFLICT (user_id) DO UPDATE SET name = EXCLUDED.name, username = EXCLUDED.username",
        (user_id, name, username),
    )


def record_single_game(user_id: int, name: str, attempts: int, username: str | None = None) -> None:
    conn = get_conn()
    cur = conn.cursor()
    _ensure_user(cur, user_id, name, username)
    cur.execute(
        """
        UPDATE users
        SET games_played = games_played + 1,
            total_attempts = total_attempts + %s,
            best_attempts = CASE
                WHEN best_attempts IS NULL OR %s < best_attempts THEN %s
                ELSE best_attempts
            END
        WHERE user_id = %s
        """,
        (attempts, attempts, attempts, user_id),
    )
    conn.commit()
    cur.close()
    conn.close()


def record_duel_result(
    winner_id: int,
    winner_name: str,
    loser_id: int,
    loser_name: str,
    winner_username: str | None = None,
    loser_username: str | None = None,
) -> None:
    conn = get_conn()
    cur = conn.cursor()
    _ensure_user(cur, winner_id, winner_name, winner_username)
    _ensure_user(cur, loser_id, loser_name, loser_username)
    cur.execute("UPDATE users SET duel_wins = duel_wins + 1 WHERE user_id = %s", (winner_id,))
    cur.execute("UPDATE users SET duel_losses = duel_losses + 1 WHERE user_id = %s", (loser_id,))
    conn.commit()
    cur.close()
    conn.close()


def record_user_seen(user_id: int, name: str, username: str | None = None) -> None:
    """/start bosgan har bir foydalanuvchini jadvalga yozib qo'yadi (o'ynasa ham, o'ynamasa ham)."""
    conn = get_conn()
    cur = conn.cursor()
    _ensure_user(cur, user_id, name, username)
    conn.commit()
    cur.close()
    conn.close()


def get_all_users() -> list[dict]:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT user_id, name, username FROM users ORDER BY user_id")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(row) for row in rows]


def get_user_stats(user_id: int) -> dict | None:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return dict(row) if row else None


def get_leaderboard(limit: int = 10) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT name, duel_wins, duel_losses FROM users "
        "WHERE duel_wins > 0 OR duel_losses > 0 "
        "ORDER BY duel_wins DESC, duel_losses ASC LIMIT %s",
        (limit,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(row) for row in rows]


def get_total_users() -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return count


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🇺🇿 O'zbek tili", callback_data="lang_uz")],
            [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")],
        ]
    )


def main_menu_keyboard(t: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t["btn_start"], callback_data="menu_start")],
            [InlineKeyboardButton(text=t["btn_duel"], callback_data="menu_duel")],
            [InlineKeyboardButton(text=t["btn_stats"], callback_data="menu_stats")],
            [InlineKeyboardButton(text=t["btn_rating"], callback_data="menu_rating")],
            [InlineKeyboardButton(text=t["btn_lang"], callback_data="menu_lang")],
            [InlineKeyboardButton(text=t["btn_age"], callback_data="menu_age")],
        ]
    )


def add_months(base: date, months: int) -> date:
    """base sanasiga `months` oy qo'shadi. Kun oy oxiridan oshsa, oy oxiriga tushadi."""
    idx = base.year * 12 + (base.month - 1) + months
    year, month0 = divmod(idx, 12)
    month = month0 + 1
    day = min(base.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def next_birthday_in_days(birth: date, today: date) -> int:
    for year in (today.year, today.year + 1):
        day = birth.day
        if birth.month == 2 and day == 29 and not calendar.isleap(year):
            day = 28
        candidate = date(year, birth.month, day)
        if candidate >= today:
            return (candidate - today).days
    return 0


def calculate_age(birth_date: date, now: datetime) -> dict:
    """
    Tug'ilgan sana (soat 00:00) dan `now` gacha aniq kalendar bo'yicha hisob.
    Kabisa yillari (29-fevral) va oylarning haqiqiy uzunligi hisobga olinadi.
    Hammasi JAMI qiymat sifatida qaytadi (oy, kun, hafta, soat, daqiqa, soniya).
    """
    today = now.date()
    if birth_date > today:
        raise ValueError("Birth date cannot be in the future.")

    total_months = (today.year - birth_date.year) * 12 + (today.month - birth_date.month)
    if add_months(birth_date, total_months) > today:
        total_months -= 1
    anniversary = add_months(birth_date, total_months)

    years, months = divmod(total_months, 12)
    extra_days = (today - anniversary).days

    total_days = (today - birth_date).days
    birth_dt = datetime.combine(birth_date, time(0, 0), tzinfo=now.tzinfo)
    total_seconds = int((now - birth_dt).total_seconds())

    return {
        "years": years,
        "months": months,
        "days": extra_days,
        "total_months": total_months,
        "extra_days": extra_days,
        "total_days": total_days,
        "total_weeks": total_days // 7,
        "extra_week_days": total_days % 7,
        "total_hours": total_seconds // 3600,
        "total_minutes": total_seconds // 60,
        "total_seconds": total_seconds,
        "next_birthday_in": next_birthday_in_days(birth_date, today),
    }


def fmt_num(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def format_age_result(t: dict, birth_date: date, now: datetime) -> str:
    r = calculate_age(birth_date, now)
    if r["next_birthday_in"] == 0:
        next_line = t["age_birthday_today"]
    else:
        next_line = t["age_next"].format(days=r["next_birthday_in"])
    return t["age_result"].format(
        birth=birth_date.strftime("%d.%m.%Y"),
        now=now.strftime("%d.%m.%Y %H:%M:%S"),
        years=r["years"],
        months=r["months"],
        days=r["days"],
        total_months=fmt_num(r["total_months"]),
        extra_days=r["extra_days"],
        total_days=fmt_num(r["total_days"]),
        total_weeks=fmt_num(r["total_weeks"]),
        extra_week_days=r["extra_week_days"],
        total_hours=fmt_num(r["total_hours"]),
        total_minutes=fmt_num(r["total_minutes"]),
        total_seconds=fmt_num(r["total_seconds"]),
        next=next_line,
    )


def _chunk(buttons: list, size: int) -> list:
    return [buttons[i:i + size] for i in range(0, len(buttons), size)]


def age_years_keyboard(t: dict, page_start: int, this_year: int) -> InlineKeyboardMarkup:
    """page_start - sahifadagi eng katta yil; pastga qarab 12 ta yil ko'rsatiladi."""
    years = [y for y in range(page_start, page_start - AGE_YEARS_PER_PAGE, -1) if y >= AGE_MIN_YEAR]
    rows = _chunk(
        [InlineKeyboardButton(text=str(y), callback_data=f"age:y:{y}") for y in years], 3
    )
    nav = []
    if page_start < this_year:
        nav.append(InlineKeyboardButton(
            text=t["age_btn_newer"],
            callback_data=f"age:yp:{min(page_start + AGE_YEARS_PER_PAGE, this_year)}",
        ))
    if page_start - AGE_YEARS_PER_PAGE >= AGE_MIN_YEAR:
        nav.append(InlineKeyboardButton(
            text=t["age_btn_older"],
            callback_data=f"age:yp:{page_start - AGE_YEARS_PER_PAGE}",
        ))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text=t["btn_menu"], callback_data="menu_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def age_months_keyboard(t: dict, year: int) -> InlineKeyboardMarkup:
    now = datetime.now(TZ)
    last_month = now.month if year == now.year else 12  # kelajak oylari ko'rsatilmaydi
    rows = _chunk(
        [
            InlineKeyboardButton(text=t["age_months"][m - 1], callback_data=f"age:m:{year}:{m}")
            for m in range(1, last_month + 1)
        ],
        3,
    )
    page_start = _age_year_page_start(year, now.year)
    rows.append([InlineKeyboardButton(text=t["age_btn_year"], callback_data=f"age:yp:{page_start}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def age_days_keyboard(t: dict, year: int, month: int) -> InlineKeyboardMarkup:
    now = datetime.now(TZ)
    last_day = calendar.monthrange(year, month)[1]  # kabisa yili shu yerda hisobga olinadi
    if (year, month) == (now.year, now.month):
        last_day = min(last_day, now.day)  # kelajak kunlari ko'rsatilmaydi
    rows = _chunk(
        [
            InlineKeyboardButton(text=str(d), callback_data=f"age:d:{year}:{month}:{d}")
            for d in range(1, last_day + 1)
        ],
        7,
    )
    rows.append([InlineKeyboardButton(text=t["age_btn_month"], callback_data=f"age:y:{year}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def age_result_keyboard(t: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t["age_again"], callback_data="age:start")],
            [InlineKeyboardButton(text=t["btn_menu"], callback_data="menu_back")],
        ]
    )


def difficulty_keyboard(t: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t["btn_easy"], callback_data="diff_50")],
            [InlineKeyboardButton(text=t["btn_medium"], callback_data="diff_100")],
            [InlineKeyboardButton(text=t["btn_hard"], callback_data="diff_500")],
        ]
    )


def cancel_duel_keyboard(t: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t["btn_cancel"], callback_data="duel_cancel")]]
    )


def menu_button_keyboard(t: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t["btn_menu"], callback_data="menu_back")]]
    )


async def get_language(state: FSMContext) -> str:
    data = await state.get_data()
    return data.get("language", "uz")


def other_user_state(bot: Bot, chat_id: int, user_id: int) -> FSMContext:
    """Boshqa foydalanuvchining FSM holatiga to'g'ridan-to'g'ri kirish uchun."""
    key = StorageKey(bot_id=bot.id, chat_id=chat_id, user_id=user_id)
    return FSMContext(storage=storage, key=key)


@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    record_user_seen(
        message.from_user.id,
        message.from_user.first_name or message.from_user.username or "Player",
        message.from_user.username,
    )
    await state.set_state(GameStates.choosing_language)
    await message.answer(TEXTS["uz"]["choose_lang"], reply_markup=language_keyboard())


@dp.message(F.text == "/admin_stats")
async def admin_stats(message: Message):
    if message.from_user.id != ADMIN_ID:
        return  # Admin bo'lmagan odamga hech qanday javob berilmaydi
    total = get_total_users()
    await message.answer(f"👥 Botdan jami foydalanuvchilar: {total} kishi")


@dp.message(F.text == "/admin_users")
async def admin_users(message: Message, bot: Bot):
    if message.from_user.id != ADMIN_ID:
        return  # Admin bo'lmagan odamga hech qanday javob berilmaydi

    users = get_all_users()
    if not users:
        await message.answer("👥 Hali hech kim botdan foydalanmagan.")
        return

    for u in users:
        username_line = f"@{u['username']}" if u["username"] else "username yo'q"
        caption = (
            f"👤 {u['name']}\n"
            f"🔗 {username_line}\n"
            f"🆔 <a href='tg://user?id={u['user_id']}'>{u['user_id']}</a>"
        )

        photo_sent = False
        try:
            photos = await bot.get_user_profile_photos(u["user_id"], limit=1)
            if photos.total_count > 0:
                file_id = photos.photos[0][-1].file_id
                await message.answer_photo(file_id, caption=caption, parse_mode="HTML")
                photo_sent = True
        except Exception:
            pass  # Rasm olinmasa, pastda oddiy matn sifatida yuboramiz

        if not photo_sent:
            await message.answer(caption + "\n🖼 Profil rasmi yo'q/yashirin", parse_mode="HTML")


@dp.callback_query(F.data.in_({"lang_uz", "lang_en"}))
async def choose_language(callback: CallbackQuery, state: FSMContext):
    language = "uz" if callback.data == "lang_uz" else "en"
    await state.update_data(language=language)
    t = TEXTS[language]
    await state.set_state(GameStates.main_menu)
    await callback.message.edit_text(t["lang_ok"])
    await callback.message.answer(t["menu_title"], reply_markup=main_menu_keyboard(t))
    await callback.answer()


@dp.callback_query(F.data == "menu_back")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    language = await get_language(state)
    t = TEXTS[language]
    await state.set_state(GameStates.main_menu)
    await callback.message.answer(t["menu_title"], reply_markup=main_menu_keyboard(t))
    await callback.answer()


@dp.callback_query(F.data == "menu_start")
async def menu_start(callback: CallbackQuery, state: FSMContext):
    language = await get_language(state)
    t = TEXTS[language]
    await state.set_state(GameStates.choosing_difficulty)
    await callback.message.answer(t["difficulty_title"], reply_markup=difficulty_keyboard(t))
    await callback.answer()


@dp.callback_query(F.data.startswith("diff_"), GameStates.choosing_difficulty)
async def choose_difficulty(callback: CallbackQuery, state: FSMContext):
    language = await get_language(state)
    t = TEXTS[language]
    max_number = int(callback.data.split("_")[1])
    secret_number = random.randint(1, max_number)

    await state.update_data(secret_number=secret_number, attempts=0)
    await state.set_state(GameStates.guessing)
    await callback.message.answer(t["think"].format(max_number=max_number))
    await callback.answer()


@dp.message(GameStates.guessing)
async def handle_guess(message: Message, state: FSMContext):
    language = await get_language(state)
    t = TEXTS[language]

    try:
        guess = int(message.text.strip())
    except (ValueError, AttributeError):
        await message.answer(t["not_number"])
        return

    data = await state.get_data()
    secret_number = data["secret_number"]
    attempts = data["attempts"] + 1
    await state.update_data(attempts=attempts)

    if guess < secret_number:
        await message.answer(t["higher"])
    elif guess > secret_number:
        await message.answer(t["lower"])
    else:
        record_single_game(
            message.from_user.id,
            message.from_user.first_name or "Player",
            attempts,
            message.from_user.username,
        )
        await state.set_state(GameStates.main_menu)
        await message.answer(t["correct"].format(attempts=attempts), reply_markup=menu_button_keyboard(t))


@dp.callback_query(F.data == "menu_stats")
async def menu_stats(callback: CallbackQuery, state: FSMContext):
    language = await get_language(state)
    t = TEXTS[language]
    stats = get_user_stats(callback.from_user.id)

    if not stats or stats["games_played"] == 0:
        await callback.message.answer(t["stats_empty"], reply_markup=menu_button_keyboard(t))
        await callback.answer()
        return

    avg = stats["total_attempts"] / stats["games_played"]
    lines = [
        t["stats_title"],
        t["stats_games"].format(games=stats["games_played"]),
        t["stats_best"].format(best=stats["best_attempts"]),
        t["stats_avg"].format(avg=f"{avg:.1f}"),
        t["stats_duel"].format(wins=stats["duel_wins"], losses=stats["duel_losses"]),
    ]
    await callback.message.answer("\n".join(lines), reply_markup=menu_button_keyboard(t))
    await callback.answer()


@dp.callback_query(F.data == "menu_rating")
async def menu_rating(callback: CallbackQuery, state: FSMContext):
    language = await get_language(state)
    t = TEXTS[language]
    leaderboard = get_leaderboard()

    if not leaderboard:
        await callback.message.answer(t["rating_empty"], reply_markup=menu_button_keyboard(t))
        await callback.answer()
        return

    lines = [t["rating_title"]]
    for rank, row in enumerate(leaderboard, start=1):
        lines.append(t["rating_row"].format(rank=rank, name=row["name"], wins=row["duel_wins"], losses=row["duel_losses"]))
    await callback.message.answer("\n".join(lines), reply_markup=menu_button_keyboard(t))
    await callback.answer()


@dp.callback_query(F.data == "menu_lang")
async def menu_change_language(callback: CallbackQuery, state: FSMContext):
    await state.set_state(GameStates.choosing_language)
    await callback.message.answer(TEXTS["uz"]["choose_lang"], reply_markup=language_keyboard())
    await callback.answer()


def _age_year_page_start(year: int, this_year: int) -> int:
    """Yil sahifalari this_year dan boshlab 12 yildan bo'linadi."""
    return this_year - ((this_year - year) // 12) * 12


async def _safe_edit(callback: CallbackQuery, text: str, markup: InlineKeyboardMarkup) -> None:
    try:
        await callback.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest:
        pass  # "message is not modified" - bir xil tugma qayta bosilganda


@dp.callback_query(F.data == "menu_age")
async def menu_age(callback: CallbackQuery, state: FSMContext):
    language = await get_language(state)
    t = TEXTS[language]
    await state.set_state(GameStates.main_menu)
    this_year = datetime.now(TZ).year
    await callback.message.answer(t["age_prompt"], reply_markup=age_years_keyboard(t, this_year, this_year))
    await callback.answer()


@dp.message(F.text.lower().in_({"/age", "/umur"}))
async def command_age(message: Message, state: FSMContext):
    language = await get_language(state)
    t = TEXTS[language]
    await state.set_state(GameStates.main_menu)
    this_year = datetime.now(TZ).year
    await message.answer(t["age_prompt"], reply_markup=age_years_keyboard(t, this_year, this_year))


@dp.callback_query(F.data == "age:start")
async def age_start(callback: CallbackQuery, state: FSMContext):
    t = TEXTS[await get_language(state)]
    this_year = datetime.now(TZ).year
    await _safe_edit(callback, t["age_prompt"], age_years_keyboard(t, this_year, this_year))
    await callback.answer()


@dp.callback_query(F.data.regexp(r"^age:yp:\d{4}$"))
async def age_year_page(callback: CallbackQuery, state: FSMContext):
    t = TEXTS[await get_language(state)]
    this_year = datetime.now(TZ).year
    page_start = int(callback.data.split(":")[2])
    page_start = min(max(page_start, AGE_MIN_YEAR), this_year)
    await _safe_edit(callback, t["age_prompt"], age_years_keyboard(t, page_start, this_year))
    await callback.answer()


@dp.callback_query(F.data.regexp(r"^age:y:\d{4}$"))
async def age_pick_year(callback: CallbackQuery, state: FSMContext):
    t = TEXTS[await get_language(state)]
    this_year = datetime.now(TZ).year
    year = int(callback.data.split(":")[2])
    if not AGE_MIN_YEAR <= year <= this_year:
        await callback.answer()
        return
    await _safe_edit(callback, t["age_pick_month"].format(year=year), age_months_keyboard(t, year))
    await callback.answer()


@dp.callback_query(F.data.regexp(r"^age:m:\d{4}:\d{1,2}$"))
async def age_pick_month(callback: CallbackQuery, state: FSMContext):
    t = TEXTS[await get_language(state)]
    _, _, y, m = callback.data.split(":")
    year, month = int(y), int(m)
    if not (AGE_MIN_YEAR <= year <= datetime.now(TZ).year and 1 <= month <= 12):
        await callback.answer()
        return
    text = t["age_pick_day"].format(year=year, month=t["age_months"][month - 1])
    await _safe_edit(callback, text, age_days_keyboard(t, year, month))
    await callback.answer()


@dp.callback_query(F.data.regexp(r"^age:d:\d{4}:\d{1,2}:\d{1,2}$"))
async def age_pick_day(callback: CallbackQuery, state: FSMContext):
    t = TEXTS[await get_language(state)]
    _, _, y, m, d = callback.data.split(":")
    try:
        birth = date(int(y), int(m), int(d))
        text = format_age_result(t, birth, datetime.now(TZ))
    except ValueError:
        await callback.answer(t["age_future"], show_alert=True)
        return
    await _safe_edit(callback, text, age_result_keyboard(t))
    await callback.answer()


# --- Duel / Matchmaking ---


@dp.callback_query(F.data == "menu_duel")
async def menu_duel(callback: CallbackQuery, state: FSMContext):
    global waiting_player, next_duel_id

    language = await get_language(state)
    t = TEXTS[language]
    user = callback.from_user
    my_name = user.first_name or user.username or "Player"

    # Hozircha navbatda hech kim yo'q -> navbatga qo'shiladi va kutadi
    if waiting_player is None:
        waiting_player = {
            "user_id": user.id,
            "chat_id": callback.message.chat.id,
            "name": my_name,
            "language": language,
        }
        await state.set_state(GameStates.duel_waiting)
        await callback.message.answer(t["duel_searching"], reply_markup=cancel_duel_keyboard(t))
        await callback.answer()
        return

    # O'zi-o'ziga qarshi turmasin
    if waiting_player["user_id"] == user.id:
        await callback.answer()
        return

    # Navbatda kimdir bor -> ikkalasini duelga ulaymiz
    opponent = waiting_player
    waiting_player = None

    duel_id = next_duel_id
    next_duel_id += 1
    secret_number = random.randint(1, DUEL_RANGE)

    active_duels[duel_id] = {
        "secret": secret_number,
        "finished": False,
        "players": {
            opponent["user_id"]: {
                "chat_id": opponent["chat_id"],
                "name": opponent["name"],
                "language": opponent["language"],
                "attempts": 0,
            },
            user.id: {
                "chat_id": callback.message.chat.id,
                "name": my_name,
                "language": language,
                "attempts": 0,
            },
        },
    }

    bot = callback.bot

    # Ikkalasining FSM holatini duel_guessing ga o'tkazamiz
    await state.set_state(GameStates.duel_guessing)
    await state.update_data(duel_id=duel_id)

    opponent_state = other_user_state(bot, opponent["chat_id"], opponent["user_id"])
    await opponent_state.set_state(GameStates.duel_guessing)
    await opponent_state.update_data(duel_id=duel_id, language=opponent["language"])

    opp_t = TEXTS[opponent["language"]]
    await bot.send_message(opponent["chat_id"], opp_t["duel_found"].format(opponent=my_name, max_number=DUEL_RANGE))
    await callback.message.answer(t["duel_found"].format(opponent=opponent["name"], max_number=DUEL_RANGE))
    await callback.answer()


@dp.callback_query(F.data == "duel_cancel", GameStates.duel_waiting)
async def cancel_duel(callback: CallbackQuery, state: FSMContext):
    global waiting_player
    language = await get_language(state)
    t = TEXTS[language]

    if waiting_player and waiting_player["user_id"] == callback.from_user.id:
        waiting_player = None

    await state.set_state(GameStates.main_menu)
    await callback.message.answer(t["duel_cancelled"])
    await callback.message.answer(t["menu_title"], reply_markup=main_menu_keyboard(t))
    await callback.answer()


@dp.message(GameStates.duel_guessing)
async def handle_duel_guess(message: Message, state: FSMContext):
    language = await get_language(state)
    t = TEXTS[language]
    data = await state.get_data()
    duel_id = data.get("duel_id")
    duel = active_duels.get(duel_id)

    if duel is None or duel["finished"]:
        await state.set_state(GameStates.main_menu)
        await message.answer(t["duel_already_finished"], reply_markup=menu_button_keyboard(t))
        return

    try:
        guess = int(message.text.strip())
    except (ValueError, AttributeError):
        await message.answer(t["not_number"])
        return

    user_id = message.from_user.id
    player = duel["players"][user_id]
    player["attempts"] += 1
    secret = duel["secret"]

    if guess < secret:
        await message.answer(t["higher"])
        return
    if guess > secret:
        await message.answer(t["lower"])
        return

    # Raqobatchi bir zumda tezroq topgan bo'lishi mumkin (race condition)
    if duel["finished"]:
        await state.set_state(GameStates.main_menu)
        await message.answer(t["duel_already_finished"], reply_markup=menu_button_keyboard(t))
        return

    duel["finished"] = True
    winner_id = user_id
    winner_name = duel["players"][winner_id]["name"]
    bot = message.bot

    loser_id = next(pid for pid in duel["players"] if pid != winner_id)
    loser_name = duel["players"][loser_id]["name"]
    record_duel_result(winner_id, winner_name, loser_id, loser_name)

    for pid, pdata in duel["players"].items():
        p_t = TEXTS[pdata["language"]]
        p_state = other_user_state(bot, pdata["chat_id"], pid)
        await p_state.set_state(GameStates.main_menu)

        if pid == winner_id:
            await bot.send_message(
                pdata["chat_id"],
                p_t["duel_win"].format(attempts=pdata["attempts"]),
                reply_markup=menu_button_keyboard(p_t),
            )
        else:
            await bot.send_message(
                pdata["chat_id"],
                p_t["duel_lose"].format(opponent=winner_name, secret=secret),
                reply_markup=menu_button_keyboard(p_t),
            )

    del active_duels[duel_id]


# --- Keep-alive server (Replit'ni doim uyg'oq tutish uchun) ---
# UptimeRobot shu "/" manzilga har necha daqiqada ping yuboradi,
# shunda Replit loyihasi "uxlab qolmaydi".

app = Flask('')


@app.route('/')
def home():
    return "Bot ishlayapti!"


def run():
    app.run(host='0.0.0.0', port=8080)


def keep_alive():
    t = Thread(target=run)
    t.start()


async def main():
    keep_alive()
    init_db()
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())