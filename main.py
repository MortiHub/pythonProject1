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

# Хранение данных о транзакциях в памяти (можно использовать для дополнительных целей)
data = {}
income_category = {}
expense_category = {}

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
        init_user_category(user_id)  # Инициализация категорий, если файла не существует
# Предустановленные категории

def init_user_category(user_id):
    income_category[user_id] = ["Продажи", "Зарплата", "Подарки"]
    expense_category[user_id] = ["Аренда", "Продукты", "Транспорт"]
    save_categories(user_id)


# Функция для загрузки данных из файла
def load_data_from_file(user_id):
    file_name = os.path.join(FILE_DIR, f'financial_report_{user_id}.xlsx')
    if os.path.exists(file_name):
        df = pd.read_excel(file_name)
        data[user_id] = df.to_dict('records')
        return True
    return False


# Функция для сохранения новой транзакции в файл
def save_transaction_to_file(user_id, transaction):
    file_name = os.path.join(FILE_DIR, f'financial_report_{user_id}.xlsx')

    # Если файл уже существует, загружаем данные, иначе создаем новый DataFrame
    if os.path.exists(file_name):
        df = pd.read_excel(file_name)
        df = pd.concat([df, pd.DataFrame([transaction])], ignore_index=True)
    else:
        df = pd.DataFrame([transaction])

    df.to_excel(file_name, index=False)


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
    load_categories(user_id)
    load_data_from_file(user_id)  # Загрузка данных из файла при старте
    bot.send_message(message.chat.id, "Привет! Я помогу вести учет денежных потоков.", reply_markup=main_keyboard())


def cancel_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(types.KeyboardButton('Отмена'))
    return keyboard


@bot.message_handler(func=lambda message: message.text == '➕Добавить приход')
def add_income(message):
    user_id = message.from_user.id
    load_data_from_file(user_id)
    load_categories(user_id)
    msg = bot.send_message(message.chat.id, "Введите сумму прихода:", reply_markup=cancel_keyboard())
    bot.register_next_step_handler(msg, process_income_amount)


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
    keyboard.add(types.KeyboardButton("Отмена"))
    return keyboard


def process_income_category(message, amount):
    if message.text == 'Отмена':
        bot.send_message(message.chat.id, "Операция отменена.", reply_markup=main_keyboard())
        return

    category = message.text
    user_id = message.from_user.id

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
    new_category = message.text     # Добавляем новую категорию в список
    user_id = message.from_user.id

    if user_id in income_category:
        income_category[user_id].append(new_category)
        save_categories(user_id)
    else:
        income_category[user_id] = [new_category]
        save_categories(user_id)    # Сохранение после добавления новой категории
    transaction = {"Дата": formatted_date, "Тип": "Приход", "Сумма": amount, "Источник": new_category}
    save_transaction(user_id, transaction)
    bot.send_message(message.chat.id, "Приход добавлен!", reply_markup=main_keyboard())


@bot.message_handler(func=lambda message: message.text == '➖Добавить расход')
def add_expense(message):
    user_id = message.from_user.id
    load_data_from_file(user_id)
    load_categories(user_id)
    msg = bot.send_message(message.chat.id, "Введите сумму расхода:", reply_markup=cancel_keyboard())
    bot.register_next_step_handler(msg, process_expense_amount)


def process_expense_amount(message):
    if message.text == 'Отмена':
        bot.send_message(message.chat.id, "Операция отменена.", reply_markup=main_keyboard())
        return
    try:
        amount = abs(float(message.text))  # Используем абсолютное значение для суммы
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
    keyboard.add(types.KeyboardButton("Отмена"))
    return keyboard


def process_expense_category(message, amount):
    if message.text == 'Отмена':
        bot.send_message(message.chat.id, "Операция отменена.", reply_markup=main_keyboard())
        return

    category = message.text
    user_id = message.from_user.id

    if category == "Добавить свою категорию":
        msg = bot.send_message(message.chat.id, "Введите название новой категории:", reply_markup=cancel_keyboard())
        if message.text == 'Отмена':
            bot.send_message(message.chat.id, "Операция отменена.", reply_markup=main_keyboard())
            return
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

     # Добавляем новую категорию в список
    user_id = message.from_user.id
    if user_id in expense_category:
        expense_category[user_id].append(new_category)
        save_categories(user_id)
    else:
        expense_category[user_id] = [new_category]
        save_categories(user_id)
    transaction = {"Дата": formatted_date, "Тип": "Расход", "Сумма": -amount, "Категория": new_category}
    save_transaction(user_id, transaction)
    bot.send_message(message.chat.id, "Расход добавлен!", reply_markup=main_keyboard())


def save_transaction(user_id, transaction):
    # Сохраняем транзакцию в памяти (опционально)
    if user_id not in data:
        data[user_id] = []
    data[user_id].append(transaction)

    # Сохраняем транзакцию в файл
    save_transaction_to_file(user_id, transaction)


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

    # Отправляем временный файл пользователю
    with open(temp_file_name, 'rb') as file:
        bot.send_document(message.chat.id, file)

    # Удаляем временный файл после отправки
    os.remove(temp_file_name)


@bot.message_handler(func=lambda message: message.text == 'Удалить таблицу')
def delete_table(message):
    user_id = message.from_user.id
    load_data_from_file(user_id)
    if user_id in data and data[user_id]:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("Да", callback_data="confirm_delete"))
        keyboard.add(types.InlineKeyboardButton("Нет", callback_data="cancel_delete"))
        bot.send_message(message.chat.id, "Вы уверены, что хотите удалить все данные?", reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, "Нет данных для удаления.", reply_markup=main_keyboard())

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