import asyncio
import os
import logging
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect("habits_pro.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (user_id INTEGER PRIMARY KEY, 
                       start_date TEXT, 
                       habit_name TEXT, 
                       daily_cost REAL,
                       failed_attempts INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

def db_query(query, params=(), fetchone=False, commit=False):
    conn = sqlite3.connect("habits_pro.db")
    cursor = conn.cursor()
    cursor.execute(query, params)
    res = cursor.fetchone() if fetchone else cursor.fetchall()
    if commit: conn.commit()
    conn.close()
    return res

# --- ЛОГИКА ЗДОРОВЬЯ ---
def get_health_status(seconds):
    hours = seconds / 3600
    days = hours / 24
    status = []
    if hours >= 2: status.append("✅ Уровень сахара в крови нормализовался")
    if hours >= 8: status.append("✅ Уровень кислорода в крови пришел в норму")
    if hours >= 24: status.append("✅ Угарный газ полностью выведен из легких")
    if days >= 2: status.append("✅ Вкусовые рецепторы и обоняние стали острее")
    if days >= 7: status.append("✅ Дыхание стало заметно легче, уходит одышка")
    if not status: status.append("⏳ Организм только начал очищение. Держись!")
    return "\n".join(status[-3:]) # Показываем последние 3 достижения

# --- ОБРАБОТЧИКИ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="🚬 Бросить курить", callback_data="setup_smoking"))
    builder.add(types.InlineKeyboardButton(text="🍺 Бросить пить", callback_data="setup_drinking"))
    builder.adjust(1)
    await message.answer("Добро пожаловать в Reset Pro. Выбери привычку, которую хочешь победить:", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("setup_"))
async def setup_cost(callback: types.CallbackQuery):
    habit = "курение" if "smoking" in callback.data else "алкоголь"
    await callback.message.edit_text(f"Ты выбрал: {habit}.\n\nСколько денег (в рублях) ты тратил на это В ДЕНЬ?\n*(Просто напиши цифру сообщением, например: 250)*")
    dp["current_habit"] = habit

@dp.message(F.text.regexp(r'^\d+$'))
async def process_cost(message: types.Message):
    habit = dp.get("current_habit", "привычка")
    cost = float(message.text)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db_query("INSERT OR REPLACE INTO users (user_id, start_date, habit_name, daily_cost) VALUES (?, ?, ?, ?)", 
             (message.from_user.id, now, habit, cost), commit=True)
    
    await message.answer(f"✅ Всё настроено!\nС этого момента ты свободен от: {habit}.\nТраты в день: {cost} руб.\n\nКоманды:\n/stats — прогресс\n/health — состояние организма\n/reset — я сорвался")

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    data = db_query("SELECT start_date, habit_name, daily_cost FROM users WHERE user_id = ?", (message.from_user.id,), fetchone=True)
    if not data: return await message.answer("Нажми /start для настройки.")
    
    start_dt = datetime.strptime(data[0], "%Y-%m-%d %H:%M:%S")
    diff = datetime.now() - start_dt
    money = (diff.total_seconds() / 86400) * data[2]
    
    await message.answer(f"🏆 **Твой результат:**\n\n"
                         f"⏳ Времени прошло: **{diff.days}д {diff.seconds//3600}ч {(diff.seconds//60)%60}м**\n"
                         f"💰 Сэкономлено: **{round(money, 2)} руб.**\n"
                         f"🚫 Привычка: {data[1]}\n\n"
                         f"Продолжай в том же духе! 💪")

@dp.message(Command("health"))
async def cmd_health(message: types.Message):
    data = db_query("SELECT start_date FROM users WHERE user_id = ?", (message.from_user.id,), fetchone=True)
    if not data: return await message.answer("Нажми /start")
    
    diff = datetime.now() - datetime.strptime(data[0], "%Y-%m-%d %H:%M:%S")
    await message.answer(f"🩺 **Статус здоровья:**\n\n{get_health_status(diff.total_seconds())}")

@dp.message(Command("reset"))
async def cmd_reset(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="❌ Да, я сорвался", callback_data="confirm_reset"))
    builder.add(types.InlineKeyboardButton(text="✅ Нет, я держусь!", callback_data="cancel_reset"))
    await message.answer("Ты уверен, что хочешь обнулить счетчик? Все достижения за этот период будут потеряны.", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "confirm_reset")
async def confirm_reset(callback: types.CallbackQuery):
    db_query("UPDATE users SET failed_attempts = failed_attempts + 1 WHERE user_id = ?", (callback.from_user.id,), commit=True)
    await callback.message.edit_text("Счетчик обнулен. Не вини себя, каждый срыв — это урок. Жми /start, чтобы начать новую попытку.")

@dp.callback_query(F.data == "cancel_reset")
async def cancel_reset(callback: types.CallbackQuery):
    await callback.message.edit_text("Фух! Правильное решение. Ты сильнее, чем твои слабости! 💪")

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
