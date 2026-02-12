import asyncio
import logging
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Включаем логирование, чтобы видеть работу бота в консоли Render
logging.basicConfig(level=logging.INFO)

# Бот будет брать токен из переменной BOT_TOKEN, которую ты указал в Render
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    logging.error("Ошибка: Переменная BOT_TOKEN не найдена в настройках!")
    exit()

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Временная память для хранения даты старта
users_db = {}

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="🚬 Бросаю курить", callback_data="quit_smoke"))
    builder.add(types.InlineKeyboardButton(text="🍺 Бросаю пить", callback_data="quit_drink"))
    builder.add(types.InlineKeyboardButton(text="💀 Всё сразу", callback_data="quit_both"))
    builder.adjust(1)
    
    await message.answer(
        "Привет! Я твой Reset-Bot.\nТвой путь к свободе начинается здесь. Что бросаем?", 
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data.startswith("quit_"))
async def callbacks_num(callback: types.CallbackQuery):
    action = callback.data.split("_")[1]
    habit = "курить" if action == "smoke" else "пить"
    if action == "both": habit = "пить и курить"
    
    users_db[callback.from_user.id] = {
        "start_date": datetime.now(),
        "habit": habit
    }
    
    await callback.message.edit_text(
        f"✅ Таймер запущен!\nТы больше не будешь {habit}.\n\nПроверить прогресс: /stats"
    )

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    user_data = users_db.get(message.from_user.id)
    if not user_data:
        await message.answer("Сначала нажми /start, чтобы запустить счетчик.")
        return

    now = datetime.now()
    delta = now - user_data["start_date"]
    
    days = delta.days
    hours = delta.seconds // 3600
    minutes = (delta.seconds // 60) % 60
    
    await message.answer(
        f"🏆 **Твой результат**\n"
        f"Ты держишься уже:\n"
        f"📅 Дней: {days}\n"
        f"⏰ Часов: {hours}\n"
        f"⏱ Минут: {minutes}\n\n"
        f"Горжусь тобой! Не сдавайся! 💪"
    )

async def main():
    # Запуск процесса опроса (polling)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
