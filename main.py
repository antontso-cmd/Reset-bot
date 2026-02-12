import asyncio
import os
import sqlite3
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
import google.generativeai as genai

# === Добавлено для Render ===
import aiohttp
from aiohttp import web

# Настройки
logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

if not BOT_TOKEN or not GEMINI_KEY:
    raise ValueError("BOT_TOKEN или GEMINI_API_KEY не найдены!")

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- БАЗА ДАННЫХ (без изменений) ---
def init_db():
    conn = sqlite3.connect("reset_pro.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (user_id INTEGER PRIMARY KEY, start_date TEXT, habit TEXT, cost REAL)''')
    conn.commit()
    conn.close()

def get_user_data(user_id):
    conn = sqlite3.connect("reset_pro.db")
    cursor = conn.cursor()
    cursor.execute("SELECT start_date, habit, cost FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res

# --- МЕНЮ (без изменений) ---
def main_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="📊 Статистика"), types.KeyboardButton(text="🩺 Здоровье"))
    builder.row(types.KeyboardButton(text="🤖 Чат с ИИ-коучем"), types.KeyboardButton(text="⚙️ Сброс"))
    return builder.as_markup(resize_keyboard=True)

# --- ТВОИ ОБРАБОТЧИКИ (без изменений) ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    init_db()
    user = get_user_data(message.from_user.id)
    if not user:
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(text="🚬 Курение", callback_data="set_smoking"))
        builder.add(types.InlineKeyboardButton(text="🍺 Алкоголь", callback_data="set_drinking"))
        await message.answer("Добро пожаловать в Reset Pro! Выбери цель:", reply_markup=builder.as_markup())
    else:
        await message.answer("С возвращением! Твой прогресс под контролем.", reply_markup=main_menu())

@dp.callback_query(F.data.startswith("set_"))
async def setup_step1(callback: types.CallbackQuery):
    habit = "курение" if "smoking" in callback.data else "алкоголь"
    dp["temp_habit"] = habit
    await callback.message.edit_text(f"Ты выбрал: {habit}. \nСколько денег в день (цифрой) ты на это тратил?")

@dp.message(lambda message: message.text.isdigit())
async def setup_step2(message: types.Message):
    habit = dp.get("temp_habit", "привычка")
    cost = float(message.text)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect("reset_pro.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?)", (message.from_user.id, now, habit, cost))
    conn.commit()
    conn.close()
    await message.answer("✅ Трекер запущен! Теперь кнопки меню всегда внизу.", reply_markup=main_menu())

@dp.message(F.text == "📊 Статистика")
async def show_stats(message: types.Message):
    data = get_user_data(message.from_user.id)
    if not data: return
    start_dt = datetime.strptime(data[0], "%Y-%m-%d %H:%M:%S")
    diff = datetime.now() - start_dt
    money = (diff.total_seconds() / 86400) * data[2]
    await message.answer(f"🏆 *Твой успех:*\n\n⏳ Ты держишься: *{diff.days}д {diff.seconds//3600}ч*\n💰 Сэкономлено: *{round(money, 2)} руб.*", parse_mode="Markdown")

@dp.message(F.text == "🩺 Здоровье")
async def show_health(message: types.Message):
    await message.answer("🩺 *Твое тело восстанавливается:*\n\n• Через 24 часа легкие очищаются от угарного газа.\n• Через 48 часов вкус и обоняние станут острее.\n• Через неделю улучшится сон.", parse_mode="Markdown")

@dp.message(F.text == "⚙️ Сброс")
async def reset_confirm(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Обнулить всё", callback_data="final_reset"))
    await message.answer("Уверен? Это сотрет все дни успеха.", reply_markup=builder.as_markup())

# --- ИИ ЧАТ (улучшил except, чтобы видеть ошибку) ---
@dp.message()
async def ai_handler(message: types.Message):
    user_data = get_user_data(message.from_user.id)
    context = f"Юзер бросает {user_data[1]}." if user_data else ""
    
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    try:
        prompt = f"Ты элитный коуч по борьбе с зависимостями. {context} Отвечай кратко, мощно и на русском. Вопрос: {message.text}"
        response = model.generate_content(prompt)
        await message.answer(response.text)
    except Exception as e:
        logging.error(f"Gemini error: {str(e)}")
        await message.answer("ИИ временно недоступен. Подожди 1–2 часа и попробуй снова.")

# === HEALTH CHECK ДЛЯ RENDER (самое важное) ===
async def health_check(request):
    return web.Response(text="Bot is alive and running 🚀")

# === ГЛАВНАЯ ФУНКЦИЯ ===
async def main():
    init_db()

    # Мини-сервер только для Render (он сам даст правильный порт)
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)

    runner = web.AppRunner(app)
    await runner.setup()
    
    # Render сам подставит PORT — мы его не трогаем
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"✅ Health check запущен на порту {port} (Render сам выбрал порт)")

    # Запускаем Telegram polling в фоне
    asyncio.create_task(dp.start_polling(bot))

    # Держим приложение живым
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
