import json
import random
import asyncio
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ===============================
# ⚙️ НАСТРОЙКИ
# ===============================
BOT_TOKEN = "8409952048:AAGeOpr8A9PKqxeo0QDHBLR6X3GZqSVZtDI"        # 👉 Токен бота
ADMIN_ID = 712270836                                                 # 👉 Твой Telegram ID
CHAT_ID = -4704627564                                                # 👉 ID общего чата

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone=ZoneInfo("Europe/Moscow"))

# ===============================
# 📁 ФАЙЛЫ
# ===============================
BIRTHDAYS_FILE = "data/birthdays.json"
USED_BDAY_FILE = "data/used_birthday_messages.json"
USED_WEEKEND_FILE = "data/used_weekend_messages.json"
WEEKEND_MESSAGES_FILE = "texts/weekend_messages.json"
BIRTHDAY_MESSAGES_FILE = "texts/birthday_messages.json"

# ===============================
# 🧰 УТИЛИТЫ
# ===============================
def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_unique_message(messages, used, used_path):
    available = [m for m in messages if m not in used]
    if not available:
        used.clear()
        save_json(used_path, used)
        available = messages.copy()
    msg = random.choice(available)
    used.append(msg)
    save_json(used_path, used)
    return msg

# ===============================
# 🌿 ПЯТНИЧНЫЕ СООБЩЕНИЯ
# ===============================
async def send_weekend_message():
    messages = load_json(WEEKEND_MESSAGES_FILE)
    used = load_json(USED_WEEKEND_FILE)
    if not messages:
        return
    text = get_unique_message(messages, used, USED_WEEKEND_FILE)
    await bot.send_message(CHAT_ID, text)

# ===============================
# 🎂 ПОЗДРАВЛЕНИЯ С ДР
# ===============================
async def send_birthday_messages():
    today = datetime.now(ZoneInfo("Europe/Moscow")).strftime("%d.%m")
    birthdays = load_json(BIRTHDAYS_FILE)
    messages = load_json(BIRTHDAY_MESSAGES_FILE)
    used = load_json(USED_BDAY_FILE)

    for user in birthdays:
        if user["date"] == today:
            msg = get_unique_message(messages, used, USED_BDAY_FILE)
            text = msg.replace("{name}", user["username"])
            await bot.send_message(CHAT_ID, text)

# ===============================
# 👑 АДМИН ПАНЕЛЬ
# ===============================
def admin_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить ДР", callback_data="add_bday")
    kb.button(text="📋 Список ДР", callback_data="list_bday")
    kb.button(text="🗑 Удалить ДР", callback_data="remove_bday")
    return kb.as_markup()

@dp.message(Command("admin"))
async def show_admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("⚙️ Админ-панель управления:", reply_markup=admin_keyboard())

# ===============================
# ➕ ДОБАВЛЕНИЕ ДР (только в личке)
# ===============================
@dp.callback_query(F.data == "add_bday")
async def start_add_bday(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    await callback.message.answer(
        "Введите список пользователей и даты в формате:\n\n"
        "<code>@username — 15.04</code>\nили несколько строк сразу:\n\n"
        "<code>@user1 — 01.01\n@user2 — 02.02</code>"
    )
    await callback.answer()

    # ✅ слушаем только личные сообщения от админа
    dp.message.register(process_add_bday, F.chat.type == "private", F.from_user.id == ADMIN_ID)


async def process_add_bday(message: types.Message):
    if message.chat.type != "private":
        return

    text = message.text.strip()
    data = load_json(BIRTHDAYS_FILE)
    added = []
    errors = []

    # регулярка: ищет @username — 15.04 (с тире и длинным тире)
    pattern = re.compile(r"@(\w+)\s*[—\-]\s*(\d{2}\.\d{2})")
    matches = pattern.findall(text)

    if not matches:
        await message.answer("❌ Неверный формат. Используй: <code>@username — 15.04</code>")
        return

    for username, date in matches:
        username = "@" + username
        if any(u["username"] == username for u in data):
            errors.append(username)
            continue
        data.append({"username": username, "date": date})
        added.append(f"{username} — {date}")

    save_json(BIRTHDAYS_FILE, data)

    reply = ""
    if added:
        reply += "✅ Добавлены:\n" + "\n".join(added)
    if errors:
        reply += "\n\n⚠️ Уже были в списке:\n" + "\n".join(errors)

    await message.answer(reply.strip(), reply_markup=admin_keyboard())

    # 🧹 очищаем временные хендлеры, чтобы не копились
    dp.message.handlers.clear()

# ===============================
# 📋 СПИСОК ДР
# ===============================
@dp.callback_query(F.data == "list_bday")
async def list_bdays(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    data = load_json(BIRTHDAYS_FILE)
    if not data:
        await callback.message.answer("📭 Список пуст.")
        return
    text = "\n".join([f"{u['username']} — {u['date']}" for u in data])
    await callback.message.answer(f"🎂 Список дней рождения:\n\n{text}", reply_markup=admin_keyboard())
    await callback.answer()

# ===============================
# 🗑 УДАЛЕНИЕ ДР
# ===============================
@dp.callback_query(F.data == "remove_bday")
async def remove_bday(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    data = load_json(BIRTHDAYS_FILE)
    if not data:
        await callback.message.answer("📭 Список пуст.")
        return
    kb = InlineKeyboardBuilder()
    for user in data:
        kb.button(text=f"Удалить {user['username']}", callback_data=f"del_{user['username']}")
    kb.button(text="↩️ Назад", callback_data="back_admin")
    await callback.message.answer("Выбери, кого удалить:", reply_markup=kb.as_markup())
    await callback.answer()

@dp.callback_query(F.data.startswith("del_"))
async def confirm_remove(callback: types.CallbackQuery):
    username = callback.data.replace("del_", "")
    data = load_json(BIRTHDAYS_FILE)
    data = [u for u in data if u["username"] != username]
    save_json(BIRTHDAYS_FILE, data)
    await callback.message.answer(f"🗑 Удалено: {username}", reply_markup=admin_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "back_admin")
async def back_admin(callback: types.CallbackQuery):
    await callback.message.answer("⚙️ Админ-панель управления:", reply_markup=admin_keyboard())
    await callback.answer()

# ===============================
# ⏰ РАСПИСАНИЕ
# ===============================
def setup_scheduler():
    scheduler.add_job(send_weekend_message, "cron", day_of_week="fri", hour=17, minute=0)
    scheduler.add_job(send_birthday_messages, "cron", hour=9, minute=0)
    scheduler.start()

# ===============================
# 🚀 MAIN
# ===============================
async def main():
    setup_scheduler()
    print("✅ WB_DevSoulBot запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
