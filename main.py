import telebot
from datetime import datetime, timedelta
import pandas as pd
from telebot import TeleBot, types
import os
import sqlite3
now = datetime.now()
formatted_date = now.strftime('%d-%m-%Y')

API_TOKEN = '7281044136:AAGwoyl2iVDfvvo_y6Qe64oW8mFv4AE4WL4'
PAYMENT_PROVIDER_TOKEN = '401643678:TEST:3a876337-7dbc-4f3f-b54a-fa6b534a7533'

bot = TeleBot(API_TOKEN)

# Папка для хранения файлов
FILE_DIR = 'data'
os.makedirs(FILE_DIR, exist_ok=True)
data = {}
income_category = {}
expense_category = {}
# Инициализация базы данных для хранения подписок
def create_db():
    conn = sqlite3.connect('subscriptions.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS subscriptions (user_id INTEGER PRIMARY KEY, active INTEGER, start_date TEXT)''')
    conn.commit()
    conn.close()

def update_subscription_status(user_id, active):
    start_date = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect('subscriptions.db')
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO subscriptions (user_id, active, start_date)
                 VALUES (?, ?, ?)''', (user_id, int(active), start_date))
    conn.commit()
    conn.close()


def get_subscription_status(user_id):
    conn = sqlite3.connect('subscriptions.db')
    c = conn.cursor()
    c.execute('''SELECT active, start_date FROM subscriptions WHERE user_id = ?''', (user_id,))
    row = c.fetchone()
    conn.close()

    if row:
        active, start_date = row
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        if active == 1 and datetime.now() <= start_date + timedelta(days=30):
            return True

    return False


# Инициализация базы данных при запуске
create_db()
# Инициализация базы данных при запуске
create_db()


def save_categories(user_id):
    income_df = pd.DataFrame(income_category[user_id], columns=["Категории"])
    expense_df = pd.DataFrame(expense_category[user_id], columns=["Категории"])

    file_path = os.path.join(FILE_DIR, f'categories_{user_id}.xlsx')

    with pd.ExcelWriter(file_path) as writer:
        income_df.to_excel(writer, sheet_name='Приход', index=False)
        expense_df.to_excel(writer, sheet_name='Расход', index=False)
def load_categories(user_id):
    file_path = os.path.join(FILE_DIR, f'categories_{user_id}.xlsx')
    if os.path.exists(file_path):
        income_df = pd.read_excel(file_path, sheet_name='Приход')
        expense_df = pd.read_excel(file_path, sheet_name='Расход')
        income_category[user_id] = income_df["Категории"].tolist()
        expense_category[user_id] = expense_df["Категории"].tolist()
    else:
        init_user_category(user_id)

def init_user_category(user_id):
    income_category[user_id] = ["Продажи", "Зарплата", "Подарки"]
    expense_category[user_id] = ["Аренда", "Продукты", "Транспорт"]
    save_categories(user_id)

def load_data_from_file(user_id):
    file_name = os.path.join(FILE_DIR, f'financial_report_{user_id}.xlsx')
    if os.path.exists(file_name):
        df = pd.read_excel(file_name)
        data[user_id] = df.to_dict('records')
        return True
    return False

def save_transaction_to_file(user_id, transaction):
    file_name = os.path.join(FILE_DIR, f'financial_report_{user_id}.xlsx')
    if os.path.exists(file_name):
        df = pd.read_excel(file_name)
        df = pd.concat([df, pd.DataFrame([transaction])], ignore_index=True)
    else:
        df = pd.DataFrame([transaction])
    df.to_excel(file_name, index=False)


# Главные кнопки
def check_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton('Доступ к подписке')
    keyboard.add(btn1)
    return keyboard

def main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton('➕Добавить приход')
    btn2 = types.KeyboardButton('➖Добавить расход')
    keyboard.add(btn1, btn2)
    keyboard.add(types.KeyboardButton('Экспорт данных'))
    keyboard.add(types.KeyboardButton('Удалить таблицу'))
    return keyboard
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if check_subscription(user_id):
        load_categories(user_id)
        load_data_from_file(user_id)
        bot.send_message(message.chat.id, "Привет! У вас есть доступ к подписке.", reply_markup=main_keyboard())
    else:
        bot.send_message(message.chat.id, "Привет! Для получения доступа, пожалуйста, оформите подписку.", reply_markup=check_keyboard())

def check_subscription(user_id):
    # Проверка статуса подписки пользователя
    return get_subscription_status(user_id)

def cancel_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(types.KeyboardButton('Отмена'))
    return keyboard

@bot.message_handler(func=lambda message: message.text == 'Доступ к подписке')
def access_subscription(message):
    user_id = message.from_user.id
    if check_subscription(user_id):
        bot.send_message(message.chat.id, "У вас есть доступ! Вы можете пользоваться ботом.", reply_markup=main_keyboard())
    else:
        bot.send_message(message.chat.id, "Для получения доступа оплатите подписку.", reply_markup=check_keyboard())
        send_invoice(message)

def send_invoice(message):
    user_id = message.from_user.id
    prices = [types.LabeledPrice(label="Подписка на месяц", amount=20000)]  # 20000 копеек = 200 рублей

    bot.send_invoice(
        chat_id=message.chat.id,
        title="Подписка на использование бота",
        description="Оформите подписку на месяц за 200 рублей",
        invoice_payload="subscription_{}".format(user_id),  # Полезная нагрузка, чтобы идентифицировать транзакцию
        provider_token=PAYMENT_PROVIDER_TOKEN,
        currency="RUB",
        prices=prices,
        start_parameter="subscription",
        is_flexible=False,  # True если сумма может варьироваться
    )

@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    user_id = message.from_user.id
    # Обновление статуса подписки в базе данных
    update_subscription_status(user_id, True)
    bot.send_message(message.chat.id, "Спасибо за оплату! Подписка активирована.", reply_markup=main_keyboard())
@bot.message_handler(func=lambda message: message.text == '➕Добавить приход')
def add_income(message):
    user_id = message.from_user.id
    if check_subscription(user_id):
        load_data_from_file(user_id)
        load_categories(user_id)
        msg = bot.send_message(message.chat.id, "Введите сумму прихода:", reply_markup=cancel_keyboard())
        bot.register_next_step_handler(msg, process_income_amount)
    else:
        bot.send_message(message.chat.id, "Привет! Для получения доступа, пожалуйста, оформите подписку.", reply_markup=check_keyboard())
def process_income_amount(message):
    if message.text == 'Отмена':
        bot.send_message(message.chat.id, "Операция отменена.", reply_markup=main_keyboard())
        return
    try:
        amount = float(message.text)
        user_id = message.from_user.id
        bot.send_message(message.chat.id, "Выберите источник прихода:", reply_markup=income_category_keyboard(user_id))
        bot.register_next_step_handler(message, process_income_category, amount)
    except ValueError:
        bot.send_message(message.chat.id, "Неправильный формат суммы. Попробуйте снова.", reply_markup=main_keyboard())

def income_category_keyboard(user_id):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for category in income_category.get(user_id, []):
        keyboard.add(types.KeyboardButton(category))
    keyboard.add(types.KeyboardButton("Добавить свой источник"))
    keyboard.add(types.KeyboardButton("Удалить источник"))
    keyboard.add(types.KeyboardButton("Отмена"))
    return keyboard

def process_income_category(message, amount):
    if message.text == 'Отмена':
        bot.send_message(message.chat.id, "Операция отменена.", reply_markup=main_keyboard())
        return

    user_id = message.from_user.id
    if message.text == "Удалить источник":
        bot.send_message(message.chat.id, "Выберите источник для удаления:", reply_markup=delete_category_keyboard(user_id, "income"))
        bot.register_next_step_handler(message, process_delete_category, "income")
        return

    category = message.text
    if category == "Добавить свой источник":
        msg = bot.send_message(message.chat.id, "Введите название нового источника:", reply_markup=cancel_keyboard())
        bot.register_next_step_handler(msg, process_new_income_category, amount)
    else:
        transaction = {"Дата": formatted_date, "Тип": "Приход", "Сумма": amount, "Источник": category}
        save_transaction(user_id, transaction)
        bot.send_message(message.chat.id, "Приход добавлен!", reply_markup=main_keyboard())

def process_new_income_category(message, amount):
    if message.text == 'Отмена':
        bot.send_message(message.chat.id, "Операция отменена.", reply_markup=main_keyboard())
        return
    new_category = message.text
    user_id = message.from_user.id

    if user_id in income_category:
        income_category[user_id].append(new_category)
    else:
        income_category[user_id] = [new_category]
    save_categories(user_id)

    transaction = {"Дата": formatted_date, "Тип": "Приход", "Сумма": amount, "Источник": new_category}
    save_transaction(user_id, transaction)
    bot.send_message(message.chat.id, "Приход добавлен!", reply_markup=main_keyboard())

@bot.message_handler(func=lambda message: message.text == '➖Добавить расход')
def add_expense(message):
    user_id = message.from_user.id
    if check_subscription(user_id):
        load_data_from_file(user_id)
        load_categories(user_id)
        msg = bot.send_message(message.chat.id, "Введите сумму расхода:", reply_markup=cancel_keyboard())
        bot.register_next_step_handler(msg, process_expense_amount)
    else:
        bot.send_message(message.chat.id, "Для получения доступа оплатите подписку.", reply_markup=check_keyboard())
def process_expense_amount(message):
    if message.text == 'Отмена':
        bot.send_message(message.chat.id, "Операция отменена.", reply_markup=main_keyboard())
        return
    try:
        amount = abs(float(message.text))
        user_id = message.from_user.id
        bot.send_message(message.chat.id, "Выберите категорию расхода:", reply_markup=expense_category_keyboard(user_id))
        bot.register_next_step_handler(message, process_expense_category, amount)
    except ValueError:
        bot.send_message(message.chat.id, "Неправильный формат суммы. Попробуйте снова.", reply_markup=main_keyboard())

def expense_category_keyboard(user_id):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for category in expense_category.get(user_id, []):
        keyboard.add(types.KeyboardButton(category))
    keyboard.add(types.KeyboardButton("Добавить свою категорию"))
    keyboard.add(types.KeyboardButton("Удалить категорию"))
    keyboard.add(types.KeyboardButton("Отмена"))
    return keyboard

def process_expense_category(message, amount):
    if message.text == 'Отмена':
        bot.send_message(message.chat.id, "Операция отменена.", reply_markup=main_keyboard())
        return

    user_id = message.from_user.id
    if message.text == "Удалить категорию":
        bot.send_message(message.chat.id, "Выберите категорию для удаления:", reply_markup=delete_category_keyboard(user_id, "expense"))
        bot.register_next_step_handler(message, process_delete_category, "expense")
        return

    category = message.text
    if category == "Добавить свою категорию":
        msg = bot.send_message(message.chat.id, "Введите название новой категории:", reply_markup=cancel_keyboard())
        bot.register_next_step_handler(msg, process_new_expense_category, amount)
    else:
        transaction = {"Дата": formatted_date, "Тип": "Расход", "Сумма": -amount, "Категория": category}
        save_transaction(user_id, transaction)
        bot.send_message(message.chat.id, "Расход добавлен!", reply_markup=main_keyboard())

def process_new_expense_category(message, amount):
    if message.text == 'Отмена':
        bot.send_message(message.chat.id, "Операция отменена.", reply_markup=main_keyboard())
        return
    new_category = message.text
    user_id = message.from_user.id

    if user_id in expense_category:
        expense_category[user_id].append(new_category)
    else:
        expense_category[user_id] = [new_category]
    save_categories(user_id)

    transaction = {"Дата": formatted_date, "Тип": "Расход", "Сумма": -amount, "Категория": new_category}
    save_transaction(user_id, transaction)
    bot.send_message(message.chat.id, "Расход добавлен!", reply_markup=main_keyboard())

def delete_category_keyboard(user_id, category_type):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    categories = income_category.get(user_id, []) if category_type == "income" else expense_category.get(user_id, [])
    for category in categories:
        keyboard.add(types.KeyboardButton(category))
    keyboard.add(types.KeyboardButton("Отмена"))
    return keyboard

def process_delete_category(message, category_type):
    if message.text == 'Отмена':
        bot.send_message(message.chat.id, "Операция отменена.", reply_markup=main_keyboard())
        return

    category = message.text
    user_id = message.from_user.id

    if category_type == "income":
        if category in income_category.get(user_id, []):
            income_category[user_id].remove(category)
            save_categories(user_id)
            bot.send_message(message.chat.id, "Источник удален!", reply_markup=main_keyboard())
        else:
            bot.send_message(message.chat.id, "Источник не найден.", reply_markup=main_keyboard())
    elif category_type == "expense":
        if category in expense_category.get(user_id, []):
            expense_category[user_id].remove(category)
            save_categories(user_id)
            bot.send_message(message.chat.id, "Категория удалена!", reply_markup=main_keyboard())
        else:
            bot.send_message(message.chat.id, "Категория не найдена.", reply_markup=main_keyboard())

def save_transaction(user_id, transaction):
    if user_id in data:
        data[user_id].append(transaction)
    else:
        data[user_id] = [transaction]
    save_transaction_to_file(user_id, transaction)

@bot.message_handler(func=lambda message: message.text == 'Экспорт данных')
def export_data(message):
    user_id = message.from_user.id
    if check_subscription(user_id):
        if user_id not in data or not data[user_id]:
            # Попытка загрузить данные из файла
            if load_data_from_file(user_id):
                bot.send_message(message.chat.id, "Данные загружены, нажмите еще раз для экспорта.",
                                 reply_markup=main_keyboard())
            else:
                bot.send_message(message.chat.id, "Нет данных для экспорта.", reply_markup=main_keyboard())
            return

        # Если данные уже загружены или были в памяти
        df = pd.DataFrame(data[user_id])

        # Добавление строки с общей суммой
        total_sum = df["Сумма"].sum()
        df_with_total = pd.concat([df, pd.DataFrame([{"Тип": "Итого", "Сумма": total_sum}])], ignore_index=True)

        # Сохраняем файл с итогом для отправки пользователю
        temp_file_name = os.path.join(FILE_DIR, f'temp_financial_report_{user_id}.xlsx')
        df_with_total.to_excel(temp_file_name, index=False)

        # Отправляем временный файл пользователю
        with open(temp_file_name, 'rb') as file:
            bot.send_document(message.chat.id, file)

        # Удаляем временный файл после отправки
        os.remove(temp_file_name)
    else:
        bot.send_message(message.chat.id, "Для получения доступа оплатите подписку.", reply_markup=check_keyboard())


@bot.message_handler(func=lambda message: message.text == 'Удалить таблицу')
def delete_data(message):
    user_id = message.from_user.id
    if check_subscription(user_id):
        load_data_from_file(user_id)
        if user_id in data and data[user_id]:
            confirm_keyboard = types.InlineKeyboardMarkup()
            confirm_keyboard.add(types.InlineKeyboardButton("Да", callback_data="confirm_delete"))
            confirm_keyboard.add(types.InlineKeyboardButton("Нет", callback_data="cancel_delete"))
            bot.send_message(message.chat.id, "Вы уверены, что хотите удалить все данные?", reply_markup=confirm_keyboard)
        else:
            bot.send_message(message.chat.id, "Нет данных для удаления.", reply_markup=main_keyboard())
    else:
        bot.send_message(message.chat.id, "Для получения доступа оплатите подписку.", reply_markup=check_keyboard())
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    if call.data == "confirm_delete":
        data[user_id] = []  # Очищаем данные в памяти
        file_name = os.path.join(FILE_DIR, f'financial_report_{user_id}.xlsx')
        if os.path.exists(file_name):
            os.remove(file_name)  # Удаляем файл
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "Данные успешно удалены.", reply_markup=main_keyboard())

    elif call.data == "cancel_delete":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "Удаление отменено.", reply_markup=main_keyboard())

if __name__ == '__main__':
    bot.polling(none_stop=True)