import os
import pandas as pd
import logging
import sqlite3
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    ConversationHandler,
    CallbackQueryHandler,
)

logging.basicConfig(level=logging.INFO)

# Replace 'YOUR_TELEGRAM_BOT_TOKEN_HERE' with your actual bot token>>
TOKEN = 'YOUR-BOT-TOKEN-HERE'

# States
(
    LANGUAGE_SELECTION,
    INCOME_AMOUNT,
    INCOME_CURRENCY,
    INCOME_COMMENT,
    EXPENSE_AMOUNT,
    EXPENSE_CURRENCY,
    EXPENSE_COMMENT,
    REPORT_SELECTION,
) = range(8)

# Database functions
def init_db():
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    # Create tables
    c.execute(
        '''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        language TEXT,
                        first_time BOOLEAN DEFAULT 1
                    )'''
    )
    c.execute(
        '''CREATE TABLE IF NOT EXISTS incomes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        date TIMESTAMP,
                        amount REAL,
                        currency TEXT,
                        comment TEXT,
                        FOREIGN KEY(user_id) REFERENCES users(user_id)
                    )'''
    )
    c.execute(
        '''CREATE TABLE IF NOT EXISTS expenses (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        date TIMESTAMP,
                        amount REAL,
                        currency TEXT,
                        comment TEXT,
                        FOREIGN KEY(user_id) REFERENCES users(user_id)
                    )'''
    )
    conn.commit()
    conn.close()


def get_user_language(user_id):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('SELECT language FROM users WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    if result:
        return result[0]
    else:
        return None


def set_user_language(user_id, language):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    if result:
        # User exists, update language and set first_time to False
        c.execute(
            'UPDATE users SET language = ?, first_time = 0 WHERE user_id = ?', (language, user_id)
        )
    else:
        # New user, insert record with first_time = 1
        c.execute(
            'INSERT INTO users (user_id, language, first_time) VALUES (?, ?, 1)',
            (user_id, language),
        )
    conn.commit()
    conn.close()


def is_first_time_user(user_id):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('SELECT first_time FROM users WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    if result:
        return bool(result[0])
    else:
        return True  # Default to True if user not found


# Language dictionary
languages = {
    'uz': {
        'start_message_new': "Salom! Kerakli bo'limni tanlang:",
        'start_message_returning': "Kerakli bo'limni tanlang:",
        'choose_language': "Iltimos, tilni tanlang:",
        'income': "⬇️Kirim",
        'expense': "⬆️Chiqim",
        'report': "🔄Hisobot",
        'settings': "⚙️Parametr",
        'enter_income_amount': "Kirim summasini kiriting:",
        'enter_expense_amount': "Chiqim summasini kiriting:",
        'choose_currency': "Pul birligini tanlang:",
        'enter_comment': "Kommentariya kiriting:",
        'data_saved': "✅Ma'lumot saqlandi",
        'choose_report': "Qaysi hisobotni ko'rmoqchisiz?",
        'weekly': "Haftalik",
        'monthly': "Oylik",
        'report_sent': "✅Hisobot yuborildi",
        'operation_cancelled': "❌Amal bekor qilindi.",
        'incorrect_selection': "Noto'g'ri tanlov.",
        'error_generating_report': "Hisobot yaratishda xatolik yuz berdi.",
        'cancel': "❌Bekor qilish",
        'change_language': "Tilni o'zgartirish",
        'select_language': "Tanlovni bajaring:",
        'invalid_amount': "Iltimos, to'g'ri summa kiriting:",
        'no_data': "Hisobot uchun ma'lumot topilmadi.",
    },
    'ru': {
        'start_message_new': "Здравствуйте! Выберите нужный раздел:",
        'start_message_returning': "Выберите нужный раздел:",
        'choose_language': "Пожалуйста, выберите язык:",
        'income': "⬇️Доход",
        'expense': "⬆️Расход",
        'report': "🔄Отчет",
        'settings': "⚙️Параметр",
        'enter_income_amount': "Введите сумму дохода:",
        'enter_expense_amount': "Введите сумму расхода:",
        'choose_currency': "Выберите валюту:",
        'enter_comment': "Введите комментарий:",
        'data_saved': "✅Данные сохранены",
        'choose_report': "Какой отчет вы хотите посмотреть?",
        'weekly': "Еженедельный",
        'monthly': "Ежемесячный",
        'report_sent': "✅Отчет отправлен",
        'operation_cancelled': "❌Операция отменена.",
        'incorrect_selection': "Неправильный выбор.",
        'error_generating_report': "Произошла ошибка при создании отчета.",
        'cancel': "❌Отмена",
        'change_language': "Изменить язык",
        'select_language': "Сделайте выбор:",
        'invalid_amount': "Пожалуйста, введите корректную сумму:",
        'no_data': "Данные для отчета не найдены.",
    },
}


def get_translation(user_id, key):
    language = get_user_language(user_id)
    if language in languages:
        return languages[language].get(key, '')
    else:
        return languages['uz'].get(key, '')


def delete_previous_bot_message(update: Update, context: CallbackContext):
    if 'last_bot_message_id' in context.user_data:
        try:
            context.bot.delete_message(
                chat_id=update.effective_chat.id, message_id=context.user_data['last_bot_message_id']
            )
        except Exception as e:
            logging.warning(f"Failed to delete bot message: {e}")


def delete_user_message(update: Update, context: CallbackContext):
    try:
        context.bot.delete_message(
            chat_id=update.effective_chat.id, message_id=update.message.message_id
        )
    except Exception as e:
        logging.warning(f"Failed to delete user message: {e}")


def delete_message(context: CallbackContext):
    job = context.job
    chat_id = job.context['chat_id']
    message_id = job.context['message_id']
    try:
        context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        logging.warning(f"Failed to delete message: {e}")


def start(update: Update, context: CallbackContext):
    init_db()  # Initialize the database
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    if language is None:
        # Ask for language selection
        keyboard = [
            [InlineKeyboardButton("O'zbekcha", callback_data='lang_uz')],
            [InlineKeyboardButton("Русский", callback_data='lang_ru')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = update.message.reply_text(
            "Iltimos, tilni tanlang:\nПожалуйста, выберите язык:", reply_markup=reply_markup
        )
        context.user_data['last_bot_message_id'] = message.message_id
        return LANGUAGE_SELECTION
    else:
        # Proceed to main menu
        show_main_menu(update, context, language)


def language_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user_id = update.effective_user.id
    data = query.data
    if data == 'lang_uz':
        set_user_language(user_id, 'uz')
        language = 'uz'
    elif data == 'lang_ru':
        set_user_language(user_id, 'ru')
        language = 'ru'
    else:
        # Should not happen
        language = 'uz'
    delete_previous_bot_message(update, context)
    show_main_menu(update, context, language)
    return ConversationHandler.END


def show_main_menu(update: Update, context: CallbackContext, language):
    keyboard = [
        [languages[language]['income'], languages[language]['expense']],
        [languages[language]['report'], languages[language]['settings']],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    chat_id = update.effective_chat.id

    user_id = update.effective_user.id
    first_time = is_first_time_user(user_id)

    if first_time:
        message_text = languages[language]['start_message_new']
        # Update first_time to False after greeting
        conn = sqlite3.connect('bot_database.db')
        c = conn.cursor()
        c.execute('UPDATE users SET first_time = 0 WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
    else:
        message_text = languages[language]['start_message_returning']

    message = context.bot.send_message(chat_id=chat_id, text=message_text, reply_markup=reply_markup)
    context.user_data['last_bot_message_id'] = message.message_id


def main_menu_selection(update: Update, context: CallbackContext):
    user_input = update.message.text
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    delete_user_message(update, context)
    delete_previous_bot_message(update, context)

    if user_input == languages[language]['income']:
        context.user_data.clear()
        income_start(update, context)
    elif user_input == languages[language]['expense']:
        context.user_data.clear()
        expense_start(update, context)
    elif user_input == languages[language]['report']:
        context.user_data.clear()
        report_start(update, context)
    elif user_input == languages[language]['settings']:
        context.user_data.clear()
        settings(update, context)
    else:
        # Send a message indicating incorrect selection
        message_text = languages[language]['incorrect_selection']
        chat_id = update.effective_chat.id
        message = context.bot.send_message(chat_id=chat_id, text=message_text)
        context.user_data['last_bot_message_id'] = message.message_id


def settings(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    keyboard = [
        [InlineKeyboardButton(languages[language]['change_language'], callback_data='change_language')],
        [InlineKeyboardButton(languages[language]['cancel'], callback_data='cancel')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message_text = languages[language]['select_language']
    chat_id = update.effective_chat.id
    message = context.bot.send_message(chat_id=chat_id, text=message_text, reply_markup=reply_markup)
    context.user_data['last_bot_message_id'] = message.message_id


def settings_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    data = query.data
    user_id = update.effective_user.id
    language = get_user_language(user_id)

    if data == 'change_language':
        # Ask for language selection
        keyboard = [
            [InlineKeyboardButton("O'zbekcha", callback_data='lang_uz')],
            [InlineKeyboardButton("Русский", callback_data='lang_ru')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        message_text = languages[language]['choose_language']
        chat_id = update.effective_chat.id
        message = context.bot.send_message(chat_id=chat_id, text=message_text, reply_markup=reply_markup)
        context.user_data['last_bot_message_id'] = message.message_id
        return LANGUAGE_SELECTION
    elif data == 'cancel':
        delete_previous_bot_message(update, context)
        show_main_menu(update, context, language)
        return ConversationHandler.END


def income_start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    keyboard = [[languages[language]['cancel']]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    message_text = languages[language]['enter_income_amount']
    chat_id = update.effective_chat.id
    message = context.bot.send_message(
        chat_id=chat_id, text=message_text, reply_markup=reply_markup
    )
    context.user_data['last_bot_message_id'] = message.message_id
    return INCOME_AMOUNT


def income_amount_received(update: Update, context: CallbackContext):
    user_input = update.message.text
    user_id = update.effective_user.id
    language = get_user_language(user_id)

    if user_input == languages[language]['cancel']:
        cancel(update, context)
        return ConversationHandler.END

    # Validate that the input is a number
    try:
        amount = float(user_input)
        context.user_data['income_amount'] = amount
        delete_user_message(update, context)
        delete_previous_bot_message(update, context)
    except ValueError:
        # Not a valid number
        delete_user_message(update, context)
        message_text = languages[language]['invalid_amount']
        keyboard = [[languages[language]['cancel']]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        message = context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message_text,
            reply_markup=reply_markup
        )
        context.user_data['last_bot_message_id'] = message.message_id
        return INCOME_AMOUNT

    keyboard = [
        [InlineKeyboardButton("USD", callback_data='USD')],
        [InlineKeyboardButton("UZS", callback_data='UZS')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message_text = languages[language]['choose_currency']
    chat_id = update.effective_chat.id
    message = context.bot.send_message(
        chat_id=chat_id, text=message_text, reply_markup=reply_markup
    )
    context.user_data['last_bot_message_id'] = message.message_id
    return INCOME_CURRENCY


def income_currency_received(update: Update, context: CallbackContext):
    query = update.callback_query
    context.user_data['income_currency'] = query.data
    query.answer()
    delete_previous_bot_message(update, context)
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    keyboard = [[languages[language]['cancel']]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    message_text = languages[language]['enter_comment']
    chat_id = update.effective_chat.id
    message = context.bot.send_message(
        chat_id=chat_id, text=message_text, reply_markup=reply_markup
    )
    context.user_data['last_bot_message_id'] = message.message_id
    return INCOME_COMMENT


def income_comment_received(update: Update, context: CallbackContext):
    user_input = update.message.text
    user_id = update.effective_user.id
    language = get_user_language(user_id)

    if user_input == languages[language]['cancel']:
        cancel(update, context)
        return ConversationHandler.END

    delete_user_message(update, context)
    delete_previous_bot_message(update, context)
    context.user_data['income_comment'] = user_input
    save_income(user_id, context.user_data)
    # Send notification and delete after 3 seconds
    chat_id = update.effective_chat.id
    message_text = languages[language]['data_saved']
    message = context.bot.send_message(chat_id=chat_id, text=message_text)
    context.job_queue.run_once(
        delete_message, 3, context={'chat_id': chat_id, 'message_id': message.message_id}
    )
    # Return to main menu
    show_main_menu(update, context, language)
    return ConversationHandler.END


def expense_start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    keyboard = [[languages[language]['cancel']]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    message_text = languages[language]['enter_expense_amount']
    chat_id = update.effective_chat.id
    message = context.bot.send_message(
        chat_id=chat_id, text=message_text, reply_markup=reply_markup
    )
    context.user_data['last_bot_message_id'] = message.message_id
    return EXPENSE_AMOUNT


def expense_amount_received(update: Update, context: CallbackContext):
    user_input = update.message.text
    user_id = update.effective_user.id
    language = get_user_language(user_id)

    if user_input == languages[language]['cancel']:
        cancel(update, context)
        return ConversationHandler.END

    # Validate that the input is a number
    try:
        amount = float(user_input)
        context.user_data['expense_amount'] = amount
        delete_user_message(update, context)
        delete_previous_bot_message(update, context)
    except ValueError:
        # Not a valid number
        delete_user_message(update, context)
        message_text = languages[language]['invalid_amount']
        keyboard = [[languages[language]['cancel']]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        message = context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message_text,
            reply_markup=reply_markup
        )
        context.user_data['last_bot_message_id'] = message.message_id
        return EXPENSE_AMOUNT

    keyboard = [
        [InlineKeyboardButton("USD", callback_data='USD')],
        [InlineKeyboardButton("UZS", callback_data='UZS')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message_text = languages[language]['choose_currency']
    chat_id = update.effective_chat.id
    message = context.bot.send_message(
        chat_id=chat_id, text=message_text, reply_markup=reply_markup
    )
    context.user_data['last_bot_message_id'] = message.message_id
    return EXPENSE_CURRENCY


def expense_currency_received(update: Update, context: CallbackContext):
    query = update.callback_query
    context.user_data['expense_currency'] = query.data
    query.answer()
    delete_previous_bot_message(update, context)
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    keyboard = [[languages[language]['cancel']]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    message_text = languages[language]['enter_comment']
    chat_id = update.effective_chat.id
    message = context.bot.send_message(
        chat_id=chat_id, text=message_text, reply_markup=reply_markup
    )
    context.user_data['last_bot_message_id'] = message.message_id
    return EXPENSE_COMMENT


def expense_comment_received(update: Update, context: CallbackContext):
    user_input = update.message.text
    user_id = update.effective_user.id
    language = get_user_language(user_id)

    if user_input == languages[language]['cancel']:
        cancel(update, context)
        return ConversationHandler.END

    delete_user_message(update, context)
    delete_previous_bot_message(update, context)
    context.user_data['expense_comment'] = user_input
    save_expense(user_id, context.user_data)
    # Send notification and delete after 3 seconds
    chat_id = update.effective_chat.id
    message_text = languages[language]['data_saved']
    message = context.bot.send_message(chat_id=chat_id, text=message_text)
    context.job_queue.run_once(
        delete_message, 3, context={'chat_id': chat_id, 'message_id': message.message_id}
    )
    # Return to main menu
    show_main_menu(update, context, language)
    return ConversationHandler.END


def report_start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    keyboard = [
        [InlineKeyboardButton(languages[language]['weekly'], callback_data='weekly')],
        [InlineKeyboardButton(languages[language]['monthly'], callback_data='monthly')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message_text = languages[language]['choose_report']
    chat_id = update.effective_chat.id
    message = context.bot.send_message(
        chat_id=chat_id, text=message_text, reply_markup=reply_markup
    )
    context.user_data['last_bot_message_id'] = message.message_id
    return REPORT_SELECTION


def report_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    selection = query.data
    query.answer()
    delete_previous_bot_message(update, context)
    user_id = update.effective_user.id
    language = get_user_language(user_id)

    try:
        file_name = create_report(user_id, selection, language)
    except Exception as e:
        logging.error(f"Error generating report: {e}")
        message_text = languages[language]['error_generating_report']
        chat_id = update.effective_chat.id
        message = context.bot.send_message(chat_id=chat_id, text=message_text)
        context.user_data['last_bot_message_id'] = message.message_id
        return ConversationHandler.END

    # Send the file
    if file_name and os.path.isfile(file_name):
        with open(file_name, 'rb') as f:
            context.bot.send_document(chat_id=update.effective_chat.id, document=f)
        # Send notification and delete after 3 seconds
        chat_id = update.effective_chat.id
        message_text = languages[language]['report_sent']
        message = context.bot.send_message(chat_id=chat_id, text=message_text)
        context.job_queue.run_once(
            delete_message, 3, context={'chat_id': chat_id, 'message_id': message.message_id}
        )
        # Remove the file after sending
        os.remove(file_name)
        # Return to main menu
        show_main_menu(update, context, language)
    else:
        message_text = languages[language]['no_data']
        chat_id = update.effective_chat.id
        message = context.bot.send_message(chat_id=chat_id, text=message_text)
        context.user_data['last_bot_message_id'] = message.message_id
        # Return to main menu
        show_main_menu(update, context, language)

    return ConversationHandler.END


def sanitize_comment(comment):
    # Limit comment length
    max_length = 200  # Adjust as needed
    sanitized = comment[:max_length]
    # Remove any non-printable characters
    sanitized = ''.join(c for c in sanitized if c.isprintable())
    return sanitized


def save_income(user_id, user_data):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    current_time = datetime.now()  # Use datetime.now()
    # Sanitize comment input
    comment = sanitize_comment(user_data['income_comment'])
    c.execute(
        'INSERT INTO incomes (user_id, date, amount, currency, comment) VALUES (?, ?, ?, ?, ?)',
        (
            user_id,
            current_time,
            user_data['income_amount'],
            user_data['income_currency'],
            comment,
        ),
    )
    conn.commit()
    conn.close()


def save_expense(user_id, user_data):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    current_time = datetime.now()  # Use datetime.now()
    # Sanitize comment input
    comment = sanitize_comment(user_data['expense_comment'])
    c.execute(
        'INSERT INTO expenses (user_id, date, amount, currency, comment) VALUES (?, ?, ?, ?, ?)',
        (
            user_id,
            current_time,
            user_data['expense_amount'],
            user_data['expense_currency'],
            comment,
        ),
    )
    conn.commit()
    conn.close()


def create_report(user_id, period, language):
    conn = sqlite3.connect('bot_database.db')
    df_income = pd.read_sql_query('SELECT * FROM incomes WHERE user_id = ?', conn, params=(user_id,))
    df_expense = pd.read_sql_query('SELECT * FROM expenses WHERE user_id = ?', conn, params=(user_id,))
    conn.close()

    if period == 'weekly':
        date_filter = datetime.now() - pd.Timedelta(days=7)
        if language == 'uz':
            file_name = 'Haftalik-hisobot.xlsx'
        else:
            file_name = 'Еженедельный-отчет.xlsx'
    elif period == 'monthly':
        date_filter = datetime.now() - pd.Timedelta(days=30)
        if language == 'uz':
            file_name = 'Oylik-hisobot.xlsx'
        else:
            file_name = 'Ежемесячный-отчет.xlsx'
    else:
        logging.error("Invalid period specified.")
        return None

    # Convert 'date' columns to datetime
    df_income['date'] = pd.to_datetime(df_income['date'])
    df_expense['date'] = pd.to_datetime(df_expense['date'])

    # Filter data based on date
    recent_income = df_income[df_income['date'] >= date_filter]
    recent_expense = df_expense[df_expense['date'] >= date_filter]

    if recent_income.empty and recent_expense.empty:
        # No data to generate report
        return None

    # Convert 'amount' column to numeric
    recent_income['amount'] = pd.to_numeric(recent_income['amount'], errors='coerce')
    recent_expense['amount'] = pd.to_numeric(recent_expense['amount'], errors='coerce')

    # Drop rows with NaN amounts
    recent_income = recent_income.dropna(subset=['amount'])
    recent_expense = recent_expense.dropna(subset=['amount'])

    # Remove 'id' and 'user_id' columns
    recent_income = recent_income.drop(columns=['id', 'user_id'])
    recent_expense = recent_expense.drop(columns=['id', 'user_id'])

    # Translate column names
    if language == 'uz':
        recent_income.rename(
            columns={
                'date': 'Sana',
                'amount': 'Summa',
                'currency': 'Valyuta',
                'comment': 'Kommentariya',
            },
            inplace=True,
        )
        recent_expense.rename(
            columns={
                'date': 'Sana',
                'amount': 'Summa',
                'currency': 'Valyuta',
                'comment': 'Kommentariya',
            },
            inplace=True,
        )
    else:
        recent_income.rename(
            columns={
                'date': 'Дата',
                'amount': 'Сумма',
                'currency': 'Валюта',
                'comment': 'Комментарий',
            },
            inplace=True,
        )
        recent_expense.rename(
            columns={
                'date': 'Дата',
                'amount': 'Сумма',
                'currency': 'Валюта',
                'comment': 'Комментарий',
            },
            inplace=True,
        )

    # Calculate total amounts by currency
    if language == 'uz':
        income_total = recent_income.groupby('Valyuta')['Summa'].sum().reset_index()
        expense_total = recent_expense.groupby('Valyuta')['Summa'].sum().reset_index()
    else:
        income_total = recent_income.groupby('Валюта')['Сумма'].sum().reset_index()
        expense_total = recent_expense.groupby('Валюта')['Сумма'].sum().reset_index()

    # Create total report dataframe
    if language == 'uz':
        total_df = pd.merge(
            income_total,
            expense_total,
            on='Valyuta',
            how='outer',
            suffixes=('_Kirim', '_Chiqim'),
        ).fillna(0)
        total_df['Balans'] = total_df['Summa_Kirim'] - total_df['Summa_Chiqim']
        # Rename columns
        total_df.rename(
            columns={
                'Valyuta': 'Valyuta',
                'Summa_Kirim': 'Umumiy Kirim',
                'Summa_Chiqim': 'Umumiy Chiqim',
                'Balans': 'Balans',
            },
            inplace=True,
        )
    else:
        total_df = pd.merge(
            income_total,
            expense_total,
            on='Валюта',
            how='outer',
            suffixes=('_Доход', '_Расход'),
        ).fillna(0)
        total_df['Баланс'] = total_df['Сумма_Доход'] - total_df['Сумма_Расход']
        # Rename columns
        total_df.rename(
            columns={
                'Валюта': 'Валюта',
                'Сумма_Доход': 'Общий Доход',
                'Сумма_Расход': 'Общий Расход',
                'Баланс': 'Баланс',
            },
            inplace=True,
        )

    with pd.ExcelWriter(file_name, engine='openpyxl') as writer:
        # Write total amounts
        if not total_df.empty:
            total_df.to_excel(
                writer, sheet_name='Umumiy Hisobot' if language == 'uz' else 'Общий Отчет', index=False
            )
        # Write detailed data
        if not recent_income.empty:
            recent_income.to_excel(
                writer, sheet_name='Kirimlar' if language == 'uz' else 'Доходы', index=False
            )
        if not recent_expense.empty:
            recent_expense.to_excel(
                writer, sheet_name='Chiqimlar' if language == 'uz' else 'Расходы', index=False
            )

    return file_name


def cancel(update: Update, context: CallbackContext):
    delete_previous_bot_message(update, context)
    delete_user_message(update, context)
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    # Send notification and delete after 3 seconds
    chat_id = update.effective_chat.id
    message_text = languages[language]['operation_cancelled']
    message = context.bot.send_message(
        chat_id=chat_id, text=message_text, reply_markup=ReplyKeyboardRemove()
    )
    context.job_queue.run_once(
        delete_message, 3, context={'chat_id': chat_id, 'message_id': message.message_id}
    )
    # Return to main menu
    show_main_menu(update, context, language)
    return ConversationHandler.END


def main():
    init_db()
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Conversation handler for language selection
    lang_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            LANGUAGE_SELECTION: [
                CallbackQueryHandler(language_selection, pattern='^lang_(uz|ru)$')
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True,
    )

    dp.add_handler(lang_conv_handler)

    # Conversation handlers for income, expense, and report
    income_conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(
                Filters.regex('^(' + languages['uz']['income'] + '|' + languages['ru']['income'] + ')$'),
                income_start,
            )
        ],
        states={
            INCOME_AMOUNT: [MessageHandler(Filters.text & ~Filters.command, income_amount_received)],
            INCOME_CURRENCY: [CallbackQueryHandler(income_currency_received, pattern='^(USD|UZS)$')],
            INCOME_COMMENT: [MessageHandler(Filters.text & ~Filters.command, income_comment_received)],
        },
        fallbacks=[
            MessageHandler(
                Filters.regex('^(' + languages['uz']['cancel'] + '|' + languages['ru']['cancel'] + ')$'),
                cancel,
            )
        ],
        allow_reentry=True,
    )

    expense_conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(
                Filters.regex('^(' + languages['uz']['expense'] + '|' + languages['ru']['expense'] + ')$'),
                expense_start,
            )
        ],
        states={
            EXPENSE_AMOUNT: [MessageHandler(Filters.text & ~Filters.command, expense_amount_received)],
            EXPENSE_CURRENCY: [CallbackQueryHandler(expense_currency_received, pattern='^(USD|UZS)$')],
            EXPENSE_COMMENT: [MessageHandler(Filters.text & ~Filters.command, expense_comment_received)],
        },
        fallbacks=[
            MessageHandler(
                Filters.regex('^(' + languages['uz']['cancel'] + '|' + languages['ru']['cancel'] + ')$'),
                cancel,
            )
        ],
        allow_reentry=True,
    )

    report_conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(
                Filters.regex('^(' + languages['uz']['report'] + '|' + languages['ru']['report'] + ')$'),
                report_start,
            )
        ],
        states={
            REPORT_SELECTION: [CallbackQueryHandler(report_selection, pattern='^(weekly|monthly)$')],
        },
        fallbacks=[
            MessageHandler(
                Filters.regex('^(' + languages['uz']['cancel'] + '|' + languages['ru']['cancel'] + ')$'),
                cancel,
            )
        ],
        allow_reentry=True,
    )

    # Add handlers to dispatcher
    dp.add_handler(income_conv_handler)
    dp.add_handler(expense_conv_handler)
    dp.add_handler(report_conv_handler)

    # Conversation handler for settings (placed after others)
    settings_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(settings_selection, pattern='^(change_language|cancel)$'),
        ],
        states={
            LANGUAGE_SELECTION: [
                CallbackQueryHandler(language_selection, pattern='^lang_(uz|ru)$')
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True,
    )

    dp.add_handler(settings_conv_handler)

    # Handler for main menu selections
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, main_menu_selection))

    # Start the bot
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
