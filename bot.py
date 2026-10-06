# TELGRAM BOT: "Guessin Game"
import asyncio
import calendar
import logging
import os
import random
from datetime import datetime, timedelta

import psycopg2
import psycopg2.extras

from aiogram import Bot, Dispatcher, F
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
        "age_title": "🎂 Umr hisoblagich",
        "age_prompt": "Tug'ilgan sanangizni kiriting:\nNamuna: 15.06.2000",
        "age_invalid": "❌ Noto'g'ri format. Iltimos quyidagi formatdan foydalaning: 15.06.2000",
        "age_future": "❌ Tug'ilgan sana kelajakdagi vaqt bo'la olmaydi. Iltimos, to'g'ri sanani kiriting.",
        "age_result": "🧮 Sizning yoringiz:\n\n{years} yil\n{months} oy\n{weeks} hafta\n{days} kun\n{hours} soat\n{minutes} daqiqa\n{seconds} soniya",
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
        "age_title": "🎂 Age Calculator",
        "age_prompt": "Enter your birth date:\nExample: 15.06.2000",
        "age_invalid": "❌ Wrong format. Please use this format: 15.06.2000",
        "age_future": "❌ Birth date cannot be in the future. Please enter a valid date.",
        "age_result": "🧮 Your age is:\n\n{years} years\n{months} months\n{weeks} weeks\n{days} days\n{hours} hours\n{minutes} minutes\n{seconds} seconds",
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
    age_calculating = State()


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


def add_months(base_date: datetime.date, months: int):
    year = base_date.year + (base_date.month - 1 + months) // 12
    month = (base_date.month - 1 + months) % 12 + 1
    day = min(base_date.day, calendar.monthrange(year, month)[1])
    return datetime.strptime(f"{year}-{month:02d}-{day:02d}", "%Y-%m-%d").date()


def parse_birth_date(value: str):
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError("Invalid date")


def calculate_age_components(birth_date, now: datetime):
    start = birth_date
    years = 0

    while True:
        next_year = add_months(start, 12)
        if next_year > now.date():
            break
        start = next_year
        years += 1

    months = 0
    while True:
        next_month = add_months(start, 1)
        if next_month > now.date():
            break
        start = next_month
        months += 1

    remaining = now - datetime.combine(start, datetime.min.time())
    total_seconds = int(remaining.total_seconds())
    weeks = remaining.days // 7
    days = remaining.days % 7
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    return {
        "years": years,
        "months": months,
        "weeks": weeks,
        "days": days,
        "hours": hours,
        "minutes": minutes,
        "seconds": seconds,
    }


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


@dp.callback_query(F.data == "menu_age")
async def menu_age(callback: CallbackQuery, state: FSMContext):
    language = await get_language(state)
    t = TEXTS[language]
    await state.set_state(GameStates.age_calculating)
    await callback.message.answer(t["age_prompt"], reply_markup=menu_button_keyboard(t))
    await callback.answer()


@dp.message(F.text.lower().in_({"/age", "/umur"}))
async def command_age(message: Message, state: FSMContext):
    language = await get_language(state)
    t = TEXTS[language]
    await state.set_state(GameStates.age_calculating)
    await message.answer(t["age_prompt"], reply_markup=menu_button_keyboard(t))


@dp.message(GameStates.age_calculating)
async def handle_age_calculation(message: Message, state: FSMContext):
    language = await get_language(state)
    t = TEXTS[language]
    raw_text = message.text.strip()

    try:
        birth_date = parse_birth_date(raw_text)
    except ValueError:
        await message.answer(t["age_invalid"], reply_markup=menu_button_keyboard(t))
        return

    now = datetime.now()
    if birth_date > now.date():
        await message.answer(t["age_future"], reply_markup=menu_button_keyboard(t))
        return

    result = calculate_age_components(birth_date, now)
    await state.set_state(GameStates.main_menu)
    await message.answer(
        t["age_result"].format(
            years=result["years"],
            months=result["months"],
            weeks=result["weeks"],
            days=result["days"],
            hours=result["hours"],
            minutes=result["minutes"],
            seconds=result["seconds"],
        ),
        reply_markup=main_menu_keyboard(t),
    )


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