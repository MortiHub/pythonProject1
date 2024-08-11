import telebot
from datetime import datetime
from telebot import types
import pandas as pd
import os
now = datetime.now()
formatted_date = now.strftime('%d-%m-%Y')
API_TOKEN = '7281044136:AAGwoyl2iVDfvvo_y6Qe64oW8mFv4AE4WL4'

bot = telebot.TeleBot(API_TOKEN)


# Папка для хранения файлов
FILE_DIR = 'data'
os.makedirs(FILE_DIR, exist_ok=True)

# Хранение данных о транзакциях
data = {}

# Предустановленные категории
income_categories = ["Продажи", "Зарплата", "Подарки"]
expense_categories = ["Аренда", "Продукты", "Транспорт"]


# Функция для загрузки данных из файла
def load_data_from_file(user_id):
    file_name = os.path.join(FILE_DIR, f'financial_report_{user_id}.xlsx')
    if os.path.exists(file_name):
        df = pd.read_excel(file_name)
        data[user_id] = df.to_dict('records')
        return True
    return False


# Главные кнопки
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
    load_data_from_file(user_id)  # Загрузка данных из файла при старте
    bot.send_message(message.chat.id, "Привет! Я помогу вести учет денежных потоков.", reply_markup=main_keyboard())


@bot.message_handler(func=lambda message: message.text == '➕Добавить приход')
def add_income(message):
    msg = bot.send_message(message.chat.id, "Введите сумму прихода:")
    bot.register_next_step_handler(msg, process_income_amount)


def process_income_amount(message):
    try:
        amount = float(message.text)
        user_id = message.from_user.id
        bot.send_message(message.chat.id, "Выберите источник прихода:", reply_markup=income_category_keyboard())
        bot.register_next_step_handler(message, process_income_category, amount)
    except ValueError:
        bot.send_message(message.chat.id, "Неправильный формат суммы. Попробуйте снова.", reply_markup=main_keyboard())


def income_category_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for category in income_categories:
        keyboard.add(types.KeyboardButton(category))
    keyboard.add(types.KeyboardButton("Добавить свой источник"))
    return keyboard


def process_income_category(message, amount):
    category = message.text
    user_id = message.from_user.id

    if category == "Добавить свой источник":
        msg = bot.send_message(message.chat.id, "Введите название нового источника:")
        bot.register_next_step_handler(msg, process_new_income_category, amount)
    else:
        save_transaction(user_id, "Приход", amount, category, is_income=True)
        bot.send_message(message.chat.id, "Приход добавлен!", reply_markup=main_keyboard())


def process_new_income_category(message, amount):
    new_category = message.text
    income_categories.append(new_category)  # Добавляем новую категорию в список
    user_id = message.from_user.id
    save_transaction(user_id, "Приход", amount, new_category, is_income=True)
    bot.send_message(message.chat.id, "Приход добавлен!", reply_markup=main_keyboard())


@bot.message_handler(func=lambda message: message.text == '➖Добавить расход')
def add_expense(message):
    msg = bot.send_message(message.chat.id, "Введите сумму расхода:")
    bot.register_next_step_handler(msg, process_expense_amount)


def process_expense_amount(message):
    try:
        amount = abs(float(message.text))  # Используем абсолютное значение для суммы
        user_id = message.from_user.id
        bot.send_message(message.chat.id, "Выберите категорию расхода:", reply_markup=expense_category_keyboard())
        bot.register_next_step_handler(message, process_expense_category, amount)
    except ValueError:
        bot.send_message(message.chat.id, "Неправильный формат суммы. Попробуйте снова.", reply_markup=main_keyboard())


def expense_category_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for category in expense_categories:
        keyboard.add(types.KeyboardButton(category))
    keyboard.add(types.KeyboardButton("Добавить свою категорию"))
    return keyboard


def process_expense_category(message, amount):
    category = message.text
    user_id = message.from_user.id

    if category == "Добавить свою категорию":
        msg = bot.send_message(message.chat.id, "Введите название новой категории:")
        bot.register_next_step_handler(msg, process_new_expense_category, amount)
    else:
        save_transaction(user_id, "Расход", -amount, category, is_income=False)
        bot.send_message(message.chat.id, "Расход добавлен!", reply_markup=main_keyboard())


def process_new_expense_category(message, amount):
    new_category = message.text
    expense_categories.append(new_category)  # Добавляем новую категорию в список
    user_id = message.from_user.id
    save_transaction(user_id, "Расход", -amount, new_category, is_income=False)
    bot.send_message(message.chat.id, "Расход добавлен!", reply_markup=main_keyboard())


def save_transaction(user_id, transaction_type, amount, category, is_income):
    if user_id not in data:
        data[user_id] = []

    transaction = {"Дата": formatted_date, "Тип": transaction_type, "Сумма": amount}

    if is_income:
        transaction["Источник"] = category  # Для прихода добавляем источник
    else:
        transaction["Категория"] = category  # Для расхода добавляем категорию

    data[user_id].append(transaction)


@bot.message_handler(func=lambda message: message.text == 'Экспорт данных')
def export_data(message):
    user_id = message.from_user.id

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

    # Удаляем строку "Итого" из DataFrame перед сохранением основного файла
    df = df[df["Тип"] != "Итого"]
    data[user_id] = df.to_dict('records')

    file_name = os.path.join(FILE_DIR, f'financial_report_{user_id}.xlsx')
    df.to_excel(file_name, index=False)

    # Отправляем временный файл пользователю
    with open(temp_file_name, 'rb') as file:
        bot.send_document(message.chat.id, file)

    # Удаляем временный файл после отправки
    os.remove(temp_file_name)


@bot.message_handler(func=lambda message: message.text == 'Удалить таблицу')
def delete_table(message):
    user_id = message.from_user.id
    if user_id in data and data[user_id]:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("Да", callback_data="confirm_delete"))
        keyboard.add(types.InlineKeyboardButton("Нет", callback_data="cancel_delete"))
        bot.send_message(message.chat.id, "Вы уверены, что хотите удалить все данные?", reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, "Нет данных для экспорта.", reply_markup=main_keyboard())

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    if call.data == "confirm_delete":
        data[user_id] = []  # Очищаем данные в памяти
        file_name = os.path.join(FILE_DIR, f'financial_report_{user_id}.xlsx')
        if os.path.exists(file_name):
            os.remove(file_name)  # Удаляем файл
        bot.send_message(call.message.chat.id, "Данные успешно удалены.", reply_markup=main_keyboard())
    elif call.data == "cancel_delete":
        bot.send_message(call.message.chat.id, "Удаление отменено.", reply_markup=main_keyboard())


if __name__ == '__main__':
    bot.polling(none_stop=True)