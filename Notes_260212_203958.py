import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Твой токен вставлен сюда
TOKEN = "8406724108:AAH1UCLZhTejHluWSsFb1kIJlAGQWMoTtzI"

# Включаем логирование
logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# База данных в памяти (сбросится при перезагрузке бота)
users_db = {}

# --- КОМАНДА /start ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="🚬 Бросаю курить", callback_data="quit_smoke"))
    builder.add(types.InlineKeyboardButton(text="🍺 Бросаю пить", callback_data="quit_drink"))
    builder.add(types.InlineKeyboardButton(text="💀 Всё сразу", callback_data="quit_both"))
    builder.adjust(1)
    
    await message.answer(
        "Привет! Я твой Reset-Bot.\nДавай начнем новую жизнь прямо сейчас.\nЧто бросаем?", 
        reply_markup=builder.as_markup()
    )

# --- ОБРАБОТКА КНОПОК ---
@dp.callback_query(F.data.startswith("quit_"))
async def callbacks_num(callback: types.CallbackQuery):
    action = callback.data.split("_")[1]
    
    if action == "smoke":
        habit = "курить"
    elif action == "drink":
        habit = "пить"
    else:
        habit = "пить и курить"
    
    # Запоминаем время нажатия
    users_db[callback.from_user.id] = {
        "start_date": datetime.now(),
        "habit": habit
    }
    
    await callback.message.edit_text(f"✅ Принято! Таймер запущен.\nТвоя цель: не {habit}.\n\nЕсли станет тяжело — пиши /help.\nЧтобы узнать прогресс — пиши /stats.")

# --- КОМАНДА /stats (Статистика) ---
@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    user_data = users_db.get(message.from_user.id)
    
    if not user_data:
        await message.answer("Таймер не запущен. Нажми /start")
        return

    now = datetime.now()
    delta = now - user_data["start_date"]
    
    days = delta.days
    seconds = delta.seconds
    hours = seconds // 3600
    minutes = (seconds // 60) % 60
    
    habit = user_data["habit"]
    
    await message.answer(
        f"🏆 **Твой прогресс**\n"
        f"Ты не {habit} уже:\n"
        f"📅 Дней: {days}\n"
        f"⏰ Часов: {hours}\n"
        f"⏱ Минут: {minutes}\n\n"
        f"Так держать! Ты сильнее привычки."
    )

# --- ЗАПУСК ---
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
