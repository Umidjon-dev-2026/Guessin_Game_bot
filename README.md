# Guessin Game — Telegram Bot

Raqam topish o'yini: yakka tartibda yoki duel (ikki kishi) rejimida.

## O'rnatish

1. Kutubxonalarni o'rnating:
   ```
   pip install -r requirements.txt
   ```

2. `.env.example` faylidan nusxa oling va `.env` deb nomlang:
   ```
   cp .env.example .env
   ```

3. `.env` faylini oching va BotFather'dan olgan tokeningizni yozing:
   ```
   BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
   ```

4. Botni ishga tushiring:
   ```
   python bot.py
   ```

## Muhim

`.env` fayl hech qachon Git'ga yuklanmaydi (`.gitignore` da ko'rsatilgan). Tokeningizni hech kimga bermang va uni ochiq kodga yozmang.
