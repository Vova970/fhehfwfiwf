import asyncio
import sqlite3
import configparser
from datetime import datetime, time
import pytz
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import io

# Чтение настроек из файла
config = configparser.ConfigParser()
config.read("settings.ini")

TOKEN = config.get("bot", "token")
CHANNEL_LINK = config.get("links", "channel_link")
CHANNEL_BACKUP = config.get("links", "channel_backup", fallback="")  # Резервный канал (необязательный)
BOT_LINK = config.get("links", "bot_link")
ADMIN_ID = int(config.get("admin", "admin_id"))

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Подключение к базе данных
def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, 
            username TEXT, 
            date TEXT,
            language TEXT DEFAULT 'ru'
        )
    """)
    conn.commit()
    return conn, conn.cursor()

conn, cursor = init_db()

# Тексты на разных языках
TEXTS = {
    "ru": {
        "welcome": "✨ Добро пожаловать в бота! ✨\n\n💎 Выбирай кнопку ниже и наслаждайся!",
        "choose_language": "🌍 Пожалуйста, выберите язык:",
        "channel_button": "💎 Основной канал",
        "channel_backup_button": "📡 Резервный канал",
        "bot_button": "🤖 Основной бот",
        "admin_button": "🔧 Админ меню",
        "back_button": "🔙 Назад",
        "admin_menu": "🔧 Админ меню",
        "stats": "📊 Статистика",
        "links": "🔗 Ссылки",
        "broadcast": "📥 Рассылка",
        "user_count": "📊 Количество пользователей: {}",
        "links_menu": "🔗 Настройки ссылок:",
        "edit_channel": "💎 Основной канал",
        "edit_channel_backup": "📡 Резервный канал",
        "edit_bot": "🤖 Основной бот",
        "send_channel_link": "💎 Пришлите новую ссылку на основной канал.",
        "send_channel_backup_link": "📡 Пришлите новую ссылку на резервный канал.",
        "send_bot_link": "🤖 Пришлите новую ссылку на бота.",
        "channel_link_updated": "✅ Ссылка на основной канал успешно изменена!",
        "channel_backup_link_updated": "✅ Ссылка на резервный канал успешно изменена!",
        "bot_link_updated": "✅ Ссылка на бота успешно изменена!",
        "main_menu": "✨ Главное меню ✨",
        "daily_stats": "📊 Ежедневная статистика:\n\n👥 Пользователей: {}",
        "invalid_link": "❌ Неверная ссылка. Пожалуйста, отправьте ссылку в формате https://t.me/...",
        "broadcast_menu": "📥 Рассылка\n\nТекст рассылки: {}",
        "broadcast_recipients": "👥 Получатели: {}\nВыбран язык: {}",
        "broadcast_start": "🚀 Запустить рассылку",
        "broadcast_select_lang": "Выберите язык получателей:",
        "broadcast_in_progress": "⏳ Рассылка началась...",
        "broadcast_complete": "✅ Рассылка завершена! Отправлено {} сообщений.",
        "broadcast_no_text": "❌ Текст рассылки пуст. Напишите сообщение для рассылки.",
        "db_sent": "📦 База данных отправлена",
        "no_access": "⛔ У вас нет доступа к этой команде"
    },
    "en": {
        "welcome": "✨ Welcome to the bot! ✨\n\n💎 Choose a button below and enjoy!",
        "choose_language": "🌍 Please choose your language:",
        "channel_button": "💎 Main channel",
        "channel_backup_button": "📡 Backup channel",
        "bot_button": "🤖 Main bot",
        "admin_button": "🔧 Admin menu",
        "back_button": "🔙 Back",
        "admin_menu": "🔧 Admin menu",
        "stats": "📊 Statistics",
        "links": "🔗 Links",
        "broadcast": "📥 Broadcast",
        "user_count": "📊 User count: {}",
        "links_menu": "🔗 Links settings:",
        "edit_channel": "💎 Main channel",
        "edit_channel_backup": "📡 Backup channel",
        "edit_bot": "🤖 Main bot",
        "send_channel_link": "💎 Send new main channel link.",
        "send_channel_backup_link": "📡 Send new backup channel link.",
        "send_bot_link": "🤖 Send new bot link.",
        "channel_link_updated": "✅ Main channel link updated successfully!",
        "channel_backup_link_updated": "✅ Backup channel link updated successfully!",
        "bot_link_updated": "✅ Bot link updated successfully!",
        "main_menu": "✨ Main menu ✨",
        "daily_stats": "📊 Daily statistics:\n\n👥 Users: {}",
        "invalid_link": "❌ Invalid link. Please send a link in format https://t.me/...",
        "broadcast_menu": "📥 Broadcast\n\nMessage text: {}",
        "broadcast_recipients": "👥 Recipients: {}\nSelected language: {}",
        "broadcast_start": "🚀 Start broadcast",
        "broadcast_select_lang": "Select recipients language:",
        "broadcast_in_progress": "⏳ Broadcast started...",
        "broadcast_complete": "✅ Broadcast complete! Sent {} messages.",
        "broadcast_no_text": "❌ Broadcast text is empty. Please write a message for broadcast.",
        "db_sent": "📦 Database sent",
        "no_access": "⛔ You don't have access to this command"
    }
}

# Получение текста на нужном языке
def get_text(lang, key, *args):
    return TEXTS[lang][key].format(*args)

# Клавиатура выбора языка (инлайн)
def get_language_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_language_ru"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="set_language_en")
        ]
    ])

# Клавиатура пользователя (инлайн)
def get_user_keyboard(user_id, lang="ru"):
    buttons = []
    
    # Кнопки каналов
    channel_buttons = [
        InlineKeyboardButton(text=get_text(lang, "channel_button"), url=CHANNEL_LINK)
    ]
    if CHANNEL_BACKUP:  # Добавляем резервную кнопку только если ссылка есть
        channel_buttons.append(
            InlineKeyboardButton(text=get_text(lang, "channel_backup_button"), url=CHANNEL_BACKUP)
        )
    buttons.append(channel_buttons)
    
    # Кнопка бота
    buttons.append([
        InlineKeyboardButton(text=get_text(lang, "bot_button"), url=BOT_LINK)
    ])
    
    if user_id == ADMIN_ID:
        buttons.append([InlineKeyboardButton(text=get_text(lang, "admin_button"), callback_data="admin_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Клавиатура "Назад"
def get_back_keyboard(lang="ru"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(lang, "back_button"), callback_data="back_to_main")]
    ])

# Клавиатура админ-меню (инлайн)
def get_admin_menu(lang="ru"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(lang, "stats"), callback_data="stats")],
        [InlineKeyboardButton(text=get_text(lang, "links"), callback_data="links")],
        [InlineKeyboardButton(text=get_text(lang, "broadcast"), callback_data="broadcast")],
        [InlineKeyboardButton(text=get_text(lang, "back_button"), callback_data="back_to_main")]
    ])

# Клавиатура рассылки
def get_broadcast_menu(lang="ru", broadcast_text=""):
    data = {
        "ru": "Все",
        "en": "All"
    }
    lang_text = data.get(lang, "All")
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(lang, "broadcast_recipients", "Все", lang_text), callback_data="broadcast_recipients")],
        [InlineKeyboardButton(text=get_text(lang, "broadcast_start"), callback_data="broadcast_start")],
        [InlineKeyboardButton(text=get_text(lang, "back_button"), callback_data="back_to_main")]
    ])

# Клавиатура выбора языка для рассылки
def get_broadcast_lang_keyboard(lang="ru"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="broadcast_lang_ru"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="broadcast_lang_en"),
            InlineKeyboardButton(text="🌍 Все", callback_data="broadcast_lang_all")
        ],
        [InlineKeyboardButton(text=get_text(lang, "back_button"), callback_data="broadcast_back")]
    ])

# Клавиатура ссылок (инлайн)
def get_links_menu(lang="ru"):
    keyboard = [
        [InlineKeyboardButton(text=get_text(lang, "edit_channel"), callback_data="edit_channel")],
        [InlineKeyboardButton(text=get_text(lang, "edit_bot"), callback_data="edit_bot")]
    ]
    
    # Добавляем кнопку редактирования резервного канала только если он используется
    if CHANNEL_BACKUP:
        keyboard.insert(1, [InlineKeyboardButton(text=get_text(lang, "edit_channel_backup"), callback_data="edit_channel_backup")])
    
    keyboard.append([InlineKeyboardButton(text=get_text(lang, "back_button"), callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Определение состояний для FSM
class Form(StatesGroup):
    waiting_for_channel_link = State()
    waiting_for_channel_backup_link = State()
    waiting_for_bot_link = State()
    waiting_for_broadcast = State()

# Хэндлер на команду /start
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or ("No username" if message.from_user.language_code == "en" else "Без имени")
    date = datetime.now().strftime("%Y-%m-%d")

    # Проверяем, есть ли пользователь в базе
    cursor.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    if user:
        lang = user[0]
        keyboard = get_user_keyboard(user_id, lang)
        await message.answer(get_text(lang, "welcome"), reply_markup=keyboard)
    else:
        # Добавляем пользователя с языком по умолчанию
        cursor.execute("INSERT INTO users (user_id, username, date) VALUES (?, ?, ?)", 
                      (user_id, username, date))
        conn.commit()
        await message.answer(get_text("ru", "choose_language"), reply_markup=get_language_keyboard())

# Хэндлер на команду /db (только для админа)
@dp.message(Command("db"))
async def send_db_handler(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        # Создаем временный файл с базой данных
        with open("users.db", "rb") as f:
            db_data = f.read()
        
        cursor.execute("SELECT language FROM users WHERE user_id = ?", (message.from_user.id,))
        lang = cursor.fetchone()[0] or "ru"
        
        await message.answer_document(
            document=types.BufferedInputFile(
                db_data,
                filename="users.db"
            ),
            caption=get_text(lang, "db_sent")
        )
    else:
        cursor.execute("SELECT language FROM users WHERE user_id = ?", (message.from_user.id,))
        lang = cursor.fetchone()[0] or "ru"
        await message.answer(get_text(lang, "no_access"))

# Хэндлер выбора языка
@dp.callback_query(lambda call: call.data.startswith("set_language_"))
async def language_choice_handler(call: types.CallbackQuery):
    lang = call.data.split("_")[-1]  # ru или en
    user_id = call.from_user.id
    
    # Обновляем язык пользователя в базе
    cursor.execute("UPDATE users SET language = ? WHERE user_id = ?", (lang, user_id))
    conn.commit()
    
    # Удаляем сообщение с выбором языка
    await call.message.delete()
    
    # Отправляем приветствие с главным меню
    keyboard = get_user_keyboard(user_id, lang)
    await call.message.answer(get_text(lang, "welcome"), reply_markup=keyboard)
    await call.answer()

# Хэндлер на кнопку "Админ меню"
@dp.callback_query(lambda call: call.data == "admin_menu")
async def admin_menu_handler(call: types.CallbackQuery):
    if call.from_user.id == ADMIN_ID:
        cursor.execute("SELECT language FROM users WHERE user_id = ?", (call.from_user.id,))
        lang = cursor.fetchone()[0] or "ru"
        await call.message.edit_text(get_text(lang, "admin_menu"), reply_markup=get_admin_menu(lang))
    await call.answer()

# Хэндлер на инлайн-кнопку "Статистика"
@dp.callback_query(lambda call: call.data == "stats")
async def stats_handler(call: types.CallbackQuery):
    cursor.execute("SELECT language FROM users WHERE user_id = ?", (call.from_user.id,))
    lang = cursor.fetchone()[0] or "ru"
    
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    await call.message.edit_text(get_text(lang, "user_count", user_count), reply_markup=get_back_keyboard(lang))
    await call.answer()

# Хэндлер на инлайн-кнопку "Ссылки"
@dp.callback_query(lambda call: call.data == "links")
async def links_handler(call: types.CallbackQuery):
    cursor.execute("SELECT language FROM users WHERE user_id = ?", (call.from_user.id,))
    lang = cursor.fetchone()[0] or "ru"
    await call.message.edit_text(get_text(lang, "links_menu"), reply_markup=get_links_menu(lang))
    await call.answer()

# Хэндлер на инлайн-кнопку "Рассылка"
@dp.callback_query(lambda call: call.data == "broadcast")
async def broadcast_handler(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id == ADMIN_ID:
        cursor.execute("SELECT language FROM users WHERE user_id = ?", (call.from_user.id,))
        lang = cursor.fetchone()[0] or "ru"
        
        # Получаем текущий текст рассылки из состояния
        data = await state.get_data()
        broadcast_text = data.get("broadcast_text", "")
        
        await call.message.edit_text(
            get_text(lang, "broadcast_menu", broadcast_text if broadcast_text else "Пусто"),
            reply_markup=get_broadcast_menu(lang, broadcast_text)
        )
        await state.set_state(Form.waiting_for_broadcast)
    await call.answer()

# Хэндлер на текстовые сообщения в режиме рассылки
@dp.message(Form.waiting_for_broadcast)
async def process_broadcast_text(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        # Сохраняем текст рассылки
        await state.update_data(broadcast_text=message.text)
        
        cursor.execute("SELECT language FROM users WHERE user_id = ?", (message.from_user.id,))
        lang = cursor.fetchone()[0] or "ru"
        
        # Обновляем меню рассылки
        await message.answer(
            get_text(lang, "broadcast_menu", message.text),
            reply_markup=get_broadcast_menu(lang, message.text)
        )

# Хэндлер на кнопку "Получатели"
@dp.callback_query(lambda call: call.data == "broadcast_recipients")
async def broadcast_recipients_handler(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id == ADMIN_ID:
        cursor.execute("SELECT language FROM users WHERE user_id = ?", (call.from_user.id,))
        lang = cursor.fetchone()[0] or "ru"
        
        # Получаем текущий выбранный язык из состояния
        data = await state.get_data()
        selected_lang = data.get("broadcast_lang", "all")
        lang_text = {
            "ru": "Русский",
            "en": "English",
            "all": "Все"
        }.get(selected_lang, "Все")
        
        # Получаем количество пользователей для каждого языка
        cursor.execute("SELECT language, COUNT(*) FROM users GROUP BY language")
        lang_counts = cursor.fetchall()
        
        total_users = sum(count for _, count in lang_counts)
        ru_count = next((count for l, count in lang_counts if l == "ru"), 0)
        en_count = next((count for l, count in lang_counts if l == "en"), 0)
        
        text = get_text(lang, "broadcast_recipients", total_users, lang_text) + "\n"
        text += f"🇷🇺 Русский: {ru_count}\n"
        text += f"🇬🇧 English: {en_count}"
        
        await call.message.edit_text(
            text,
            reply_markup=get_broadcast_lang_keyboard(lang)
        )
    await call.answer()

# Хэндлер на выбор языка для рассылки
@dp.callback_query(lambda call: call.data.startswith("broadcast_lang_"))
async def broadcast_lang_handler(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id == ADMIN_ID:
        selected_lang = call.data.split("_")[-1]  # ru, en или all
        await state.update_data(broadcast_lang=selected_lang)
        
        cursor.execute("SELECT language FROM users WHERE user_id = ?", (call.from_user.id,))
        lang = cursor.fetchone()[0] or "ru"
        
        # Возвращаемся в меню рассылки
        data = await state.get_data()
        broadcast_text = data.get("broadcast_text", "")
        
        await call.message.edit_text(
            get_text(lang, "broadcast_menu", broadcast_text if broadcast_text else "Пусто"),
            reply_markup=get_broadcast_menu(lang, broadcast_text)
        )
    await call.answer()

# Хэндлер на кнопку "Назад" из меню выбора языка рассылки
@dp.callback_query(lambda call: call.data == "broadcast_back")
async def broadcast_back_handler(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id == ADMIN_ID:
        cursor.execute("SELECT language FROM users WHERE user_id = ?", (call.from_user.id,))
        lang = cursor.fetchone()[0] or "ru"
        
        data = await state.get_data()
        broadcast_text = data.get("broadcast_text", "")
        
        await call.message.edit_text(
            get_text(lang, "broadcast_menu", broadcast_text if broadcast_text else "Пусто"),
            reply_markup=get_broadcast_menu(lang, broadcast_text)
        )
    await call.answer()

# Хэндлер на кнопку "Запустить рассылку"
@dp.callback_query(lambda call: call.data == "broadcast_start")
async def broadcast_start_handler(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id == ADMIN_ID:
        cursor.execute("SELECT language FROM users WHERE user_id = ?", (call.from_user.id,))
        lang = cursor.fetchone()[0] or "ru"
        
        data = await state.get_data()
        broadcast_text = data.get("broadcast_text", "")
        broadcast_lang = data.get("broadcast_lang", "all")
        
        if not broadcast_text:
            await call.answer(get_text(lang, "broadcast_no_text"), show_alert=True)
            return
        
        await call.answer(get_text(lang, "broadcast_in_progress"))
        
        # Получаем пользователей для рассылки
        if broadcast_lang == "all":
            cursor.execute("SELECT user_id FROM users WHERE user_id != ?", (ADMIN_ID,))
        else:
            cursor.execute("SELECT user_id FROM users WHERE language = ? AND user_id != ?", (broadcast_lang, ADMIN_ID))
        
        users = cursor.fetchall()
        success = 0
        
        for user in users:
            try:
                await bot.send_message(user[0], broadcast_text)
                success += 1
            except:
                continue
        
        await call.message.answer(get_text(lang, "broadcast_complete", success))
    else:
        await call.answer()

# Хэндлер на инлайн-кнопку "Основной канал"
@dp.callback_query(lambda call: call.data == "edit_channel")
async def edit_channel_handler(call: types.CallbackQuery, state: FSMContext):
    cursor.execute("SELECT language FROM users WHERE user_id = ?", (call.from_user.id,))
    lang = cursor.fetchone()[0] or "ru"
    await call.message.edit_text(get_text(lang, "send_channel_link"), reply_markup=get_back_keyboard(lang))
    await state.set_state(Form.waiting_for_channel_link)
    await call.answer()

# Хэндлер на инлайн-кнопку "Резервный канал"
@dp.callback_query(lambda call: call.data == "edit_channel_backup")
async def edit_channel_backup_handler(call: types.CallbackQuery, state: FSMContext):
    cursor.execute("SELECT language FROM users WHERE user_id = ?", (call.from_user.id,))
    lang = cursor.fetchone()[0] or "ru"
    await call.message.edit_text(get_text(lang, "send_channel_backup_link"), reply_markup=get_back_keyboard(lang))
    await state.set_state(Form.waiting_for_channel_backup_link)
    await call.answer()

# Хэндлер на инлайн-кнопку "Основной бот"
@dp.callback_query(lambda call: call.data == "edit_bot")
async def edit_bot_handler(call: types.CallbackQuery, state: FSMContext):
    cursor.execute("SELECT language FROM users WHERE user_id = ?", (call.from_user.id,))
    lang = cursor.fetchone()[0] or "ru"
    await call.message.edit_text(get_text(lang, "send_bot_link"), reply_markup=get_back_keyboard(lang))
    await state.set_state(Form.waiting_for_bot_link)
    await call.answer()

# Хэндлер на изменение ссылки на основной канал
@dp.message(Form.waiting_for_channel_link)
async def change_channel_link(message: types.Message, state: FSMContext):
    cursor.execute("SELECT language FROM users WHERE user_id = ?", (message.from_user.id,))
    lang = cursor.fetchone()[0] or "ru"
    
    if not message.text.startswith("https://t.me/"):
        await message.answer(get_text(lang, "invalid_link"))
        return
    
    global CHANNEL_LINK
    CHANNEL_LINK = message.text
    config.set("links", "channel_link", CHANNEL_LINK)
    with open("settings.ini", "w") as configfile:
        config.write(configfile)
    await message.answer(get_text(lang, "channel_link_updated"), reply_markup=get_user_keyboard(message.from_user.id, lang))
    await state.clear()

# Хэндлер на изменение ссылки на резервный канал
@dp.message(Form.waiting_for_channel_backup_link)
async def change_channel_backup_link(message: types.Message, state: FSMContext):
    cursor.execute("SELECT language FROM users WHERE user_id = ?", (message.from_user.id,))
    lang = cursor.fetchone()[0] or "ru"
    
    if not message.text.startswith("https://t.me/"):
        await message.answer(get_text(lang, "invalid_link"))
        return
    
    global CHANNEL_BACKUP
    CHANNEL_BACKUP = message.text
    config.set("links", "channel_backup", CHANNEL_BACKUP)
    with open("settings.ini", "w") as configfile:
        config.write(configfile)
    await message.answer(get_text(lang, "channel_backup_link_updated"), reply_markup=get_user_keyboard(message.from_user.id, lang))
    await state.clear()

# Хэндлер на изменение ссылки на бота
@dp.message(Form.waiting_for_bot_link)
async def change_bot_link(message: types.Message, state: FSMContext):
    cursor.execute("SELECT language FROM users WHERE user_id = ?", (message.from_user.id,))
    lang = cursor.fetchone()[0] or "ru"
    
    if not message.text.startswith("https://t.me/"):
        await message.answer(get_text(lang, "invalid_link"))
        return
    
    global BOT_LINK
    BOT_LINK = message.text
    config.set("links", "bot_link", BOT_LINK)
    with open("settings.ini", "w") as configfile:
        config.write(configfile)
    await message.answer(get_text(lang, "bot_link_updated"), reply_markup=get_user_keyboard(message.from_user.id, lang))
    await state.clear()

# Хэндлер на кнопку "Назад"
@dp.callback_query(lambda call: call.data == "back_to_main")
async def back_handler(call: types.CallbackQuery, state: FSMContext):
    cursor.execute("SELECT language FROM users WHERE user_id = ?", (call.from_user.id,))
    lang = cursor.fetchone()[0] or "ru"
    await state.clear()
    await call.message.edit_text(get_text(lang, "main_menu"), reply_markup=get_user_keyboard(call.from_user.id, lang))
    await call.answer()

# Хэндлер на любые текстовые сообщения (если пользователь не в состоянии)
@dp.message()
async def handle_other_messages(message: types.Message):
    cursor.execute("SELECT language FROM users WHERE user_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    
    if user:
        lang = user[0]
        keyboard = get_user_keyboard(message.from_user.id, lang)
        await message.answer(get_text(lang, "main_menu"), reply_markup=keyboard)
    else:
        await message.answer(get_text("ru", "choose_language"), reply_markup=get_language_keyboard())

# Функция для отправки ежедневной статистики
async def send_daily_stats():
    while True:
        now = datetime.now(pytz.timezone('Europe/Kiev'))
        if now.time() >= time(0, 0) and now.time() <= time(0, 1):
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            stats_text = get_text("ru", "daily_stats", user_count)
            await bot.send_message(ADMIN_ID, stats_text)
        await asyncio.sleep(60)

# Запуск бота
async def main():
    # Запускаем задачу для ежедневной статистики
    asyncio.create_task(send_daily_stats())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())