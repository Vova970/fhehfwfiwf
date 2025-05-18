import sqlite3
from datetime import datetime, timedelta
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Конфигурация бота
TOKEN = '7412080065:AAGFF-h8r2REqDan8YKwFkH2vU41v1tYfz8'
ADMIN_IDS = [8126533622]  # Сюда будут добавляться админы через команду /makeadmin

# Инициализация базы данных
conn = sqlite3.connect('bot_database.db', check_same_thread=False)
cursor = conn.cursor()

# Создание таблиц
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    last_interaction DATE,
    blocked BOOLEAN DEFAULT FALSE
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
''')

conn.commit()

# Функции для работы с базой данных
def add_user(user_id, username, first_name, last_name):
    cursor.execute('''
    INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, last_interaction)
    VALUES (?, ?, ?, ?, ?)
    ''', (user_id, username, first_name, last_name, datetime.now().date()))
    conn.commit()

def update_user_interaction(user_id):
    cursor.execute('''
    UPDATE users SET last_interaction = ?, blocked = FALSE
    WHERE user_id = ?
    ''', (datetime.now().date(), user_id))
    conn.commit()

def get_start_message():
    cursor.execute('SELECT value FROM settings WHERE key = "start_message"')
    result = cursor.fetchone()
    return result[0] if result else "Добро пожаловать! Это стандартное сообщение."

def set_start_message(text):
    cursor.execute('''
    INSERT OR REPLACE INTO settings (key, value)
    VALUES (?, ?)
    ''', ('start_message', text))
    conn.commit()

def get_user_stats():
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    cursor.execute('SELECT COUNT(*) FROM users WHERE last_interaction = ? AND blocked = FALSE', (today,))
    today_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM users WHERE last_interaction = ? AND blocked = FALSE', (yesterday,))
    yesterday_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM users WHERE blocked = FALSE')
    total_count = cursor.fetchone()[0]
    
    return today_count, yesterday_count, total_count

def get_all_users():
    cursor.execute('SELECT user_id FROM users WHERE blocked = FALSE')
    return [row[0] for row in cursor.fetchall()]

def mark_user_blocked(user_id):
    cursor.execute('UPDATE users SET blocked = TRUE WHERE user_id = ?', (user_id,))
    conn.commit()

def is_admin(user_id):
    return user_id in ADMIN_IDS

def add_admin(user_id):
    if user_id not in ADMIN_IDS:
        ADMIN_IDS.append(user_id)

# Обработчики команд
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username, user.first_name, user.last_name)
    update_user_interaction(user.id)
    
    start_message = get_start_message()
    await update.message.reply_text(start_message)

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data='admin_stats')],
        [InlineKeyboardButton("✉️ Сообщение", callback_data='admin_message')],
        [InlineKeyboardButton("📥 Рассылка", callback_data='admin_broadcast')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Админ меню:", reply_markup=reply_markup)

async def db_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        return
    
    with open('bot_database.db', 'rb') as db_file:
        await context.bot.send_document(chat_id=user.id, document=db_file)

async def makeadmin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        return
    
    if not context.args:
        await update.message.reply_text("Использование: /makeadmin <user_id>")
        return
    
    try:
        new_admin_id = int(context.args[0])
        add_admin(new_admin_id)
        await update.message.reply_text(f"Пользователь {new_admin_id} теперь админ")
    except ValueError:
        await update.message.reply_text("Некорректный ID пользователя")

# Обработчики callback-ов
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    
    if not is_admin(user.id) and query.data.startswith('admin_'):
        return
    
    if query.data == 'admin_stats':
        await show_stats(query)
    elif query.data == 'admin_message':
        await query.edit_message_text("Отправьте новое сообщение для команды /start:")
        context.user_data['waiting_for_message'] = True
    elif query.data == 'admin_broadcast':
        keyboard = [
            [InlineKeyboardButton("Запустить рассылку", callback_data='confirm_broadcast')],
            [InlineKeyboardButton("Назад", callback_data='back_to_admin')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📥 Рассылка", reply_markup=reply_markup)
    elif query.data == 'confirm_broadcast':
        await query.edit_message_text("Отправьте сообщение для рассылки:")
        context.user_data['waiting_for_broadcast'] = True
    elif query.data == 'back_to_admin':
        await admin_menu(query)

async def show_stats(query):
    today, yesterday, total = get_user_stats()
    keyboard = [
        [InlineKeyboardButton("Обновить", callback_data='admin_stats')],
        [InlineKeyboardButton("Назад", callback_data='back_to_admin')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        f"📊 Статистика\n\n"
        f"🤖 Взаимодействовало с ботом\n"
        f"Сегодня: {today} человек\n"
        f"Вчера: {yesterday} человек\n"
        f"Всего: {total} человек",
        reply_markup=reply_markup
    )

async def admin_menu(query):
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data='admin_stats')],
        [InlineKeyboardButton("✉️ Сообщение", callback_data='admin_message')],
        [InlineKeyboardButton("📥 Рассылка", callback_data='admin_broadcast')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Админ меню:", reply_markup=reply_markup)

# Обработчик текстовых сообщений
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    update_user_interaction(user.id)
    
    if 'waiting_for_message' in context.user_data and is_admin(user.id):
        set_start_message(update.message.text)
        context.user_data.pop('waiting_for_message')
        await update.message.reply_text("Сообщение для /start обновлено!")
        await admin_command(update, context)
    elif 'waiting_for_broadcast' in context.user_data and is_admin(user.id):
        context.user_data.pop('waiting_for_broadcast')
        broadcast_message = update.message.text
        users = get_all_users()
        success = 0
        failed = 0
        
        for user_id in users:
            try:
                await context.bot.send_message(chat_id=user_id, text=broadcast_message)
                success += 1
            except:
                mark_user_blocked(user_id)
                failed += 1
        
        await update.message.reply_text(f"Рассылка завершена!\nУспешно: {success}\nНе доставлено: {failed}")
        await admin_command(update, context)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    if update and hasattr(update, 'effective_user'):
        mark_user_blocked(update.effective_user.id)
    print(f"Error: {context.error}")

def main():
    application = Application.builder().token(TOKEN).build()

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("db", db_command))
    application.add_handler(CommandHandler("makeadmin", makeadmin_command))

    # Обработчики кнопок
    application.add_handler(CallbackQueryHandler(button_handler))

    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    # Обработчик ошибок
    application.add_error_handler(error_handler)

    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()
