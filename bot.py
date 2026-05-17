import asyncio
import contextlib
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import TELEGRAM_TOKEN, ACCESS_KEY, AUTHORIZED_USERS_FILE, LINKS_FILE
from browser_manager import (
    is_monitoring_enabled,
    monitor_links,
    start_monitoring,
    stop_monitoring,
)
from telegram_utils import close_notify_bot_session

bot = Bot(
    token=TELEGRAM_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# FSM
class AddLink(StatesGroup):
    name = State()
    url = State()

# Авторизация
def load_users():
    try:
        with open(AUTHORIZED_USERS_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_users(users):
    with open(AUTHORIZED_USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def is_authorized(user_id):
    return user_id in load_users()

# Кнопки
def menu_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить", callback_data="add")
    kb.button(text="🗑️ Удалить", callback_data="remove")
    kb.button(text="📋 Список", callback_data="list")
    kb.button(text="🧹 Очистить всё", callback_data="clean")

    if is_monitoring_enabled():
        kb.button(text="⏹️ Стоп", callback_data="stop_monitoring")
    else:
        kb.button(text="▶️ Старт", callback_data="start_monitoring")

    kb.adjust(2, 2, 1)  # две кнопки в ряд и отдельная кнопка запуска/остановки
    return kb.as_markup()

@dp.message(F.text == "/start")
async def start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if is_authorized(user_id):
        await message.answer("👋 Добро пожаловать!", reply_markup=menu_kb())
    else:
        await message.answer("🔐 Введите ключ доступа:")

@dp.message(F.text == ACCESS_KEY)
async def auth_key(message: types.Message):
    user_id = message.from_user.id
    users = load_users()
    if user_id not in users:
        users.append(user_id)
        save_users(users)
    await message.answer("✅ Успешная авторизация!", reply_markup=menu_kb())

@dp.callback_query(F.data == "add")
async def callback_add(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🔤 Введите название ссылки:")
    await state.set_state(AddLink.name)

@dp.message(AddLink.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer("🌍 Теперь отправьте саму ссылку:")
    await state.set_state(AddLink.url)

@dp.message(AddLink.url)
async def process_url(message: types.Message, state: FSMContext):
    data = await state.get_data()
    name = data["name"]
    url = message.text.strip()

    try:
        with open(LINKS_FILE, "r", encoding="utf-8") as f:
            links = json.load(f)
    except:
        links = []

    if any(item.get("url") == url for item in links):
        await message.answer(
            "⚠️ Такая ссылка уже есть в списке.",
            reply_markup=menu_kb(),
        )
        await state.clear()
        return


    links.append({"name": name, "url": url})

    with open(LINKS_FILE, "w", encoding="utf-8") as f:
        json.dump(links, f, indent=2)
        
    await message.answer(f"✅ Добавлено: <a href=\"{url}\">{name}</a>", reply_markup=menu_kb())
    await state.clear()

@dp.callback_query(F.data == "list")
async def callback_list(callback: types.CallbackQuery):
    try:
        with open(LINKS_FILE, "r", encoding="utf-8") as f:
            links = json.load(f)
        text = "\n".join([f"🔗 <a href=\"{link['url']}\">{link['name']}</a>" for link in links]) or "❌ Список пуст."
    except:
        text = "❌ Не удалось загрузить список."
    await callback.message.edit_text(text, reply_markup=menu_kb())

@dp.callback_query(F.data == "remove")
async def callback_remove(callback: types.CallbackQuery):
    with open(LINKS_FILE, "r", encoding="utf-8") as f:
        links = json.load(f)

    kb = InlineKeyboardBuilder()
    for i, link in enumerate(links):
        kb.button(text=link["name"], callback_data=f"del_{i}")
    kb.button(text="⬅️ Назад", callback_data="menu")
    await callback.message.edit_text("🗑️ Выберите ссылку для удаления:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("del_"))
async def delete_link(callback: types.CallbackQuery):
    index = int(callback.data.split("_")[1])
    with open(LINKS_FILE, "r", encoding="utf-8") as f:
        links = json.load(f)
    removed = links.pop(index)
    with open(LINKS_FILE, "w", encoding="utf-8") as f:
        json.dump(links, f, indent=2)
    await callback.message.edit_text(f"🗑️ Удалено: {removed['name']}", reply_markup=menu_kb())

@dp.callback_query(F.data == "clean")
async def callback_clean(callback: types.CallbackQuery):
    with open(LINKS_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)
    await callback.message.edit_text("🧹 Все ссылки удалены.", reply_markup=menu_kb())

@dp.callback_query(F.data == "menu")
async def callback_menu(callback: types.CallbackQuery):
    await callback.message.edit_text("📋 Главное меню", reply_markup=menu_kb())

@dp.callback_query(F.data == "start_monitoring")
async def callback_start_monitoring(callback: types.CallbackQuery):
    started = await start_monitoring()

    if started:
        await callback.message.edit_text("▶️ Поиск запущен.", reply_markup=menu_kb())
    else:
        await callback.message.edit_text("✅ Поиск уже активен.", reply_markup=menu_kb())

    await callback.answer()


@dp.callback_query(F.data == "stop_monitoring")
async def callback_stop_monitoring(callback: types.CallbackQuery):
    stopped = await stop_monitoring(reason="ручная остановка из Telegram")

    if stopped:
        await callback.message.edit_text("⏹️ Поиск остановлен.", reply_markup=menu_kb())
    else:
        await callback.message.edit_text("✅ Поиск уже остановлен.", reply_markup=menu_kb())

    await callback.answer()

# Старт
async def main():
    monitor_task = asyncio.create_task(monitor_links())

    try:
        await dp.start_polling(bot)
    finally:
        monitor_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await monitor_task
        await close_notify_bot_session()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
