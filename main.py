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


# Функция для загрузки данных из файла при перезапуске
def load_data_from_file(user_id):
    file_name = os.path.join(FILE_DIR, f'financial_report_{user_id}.xlsx')
    if os.path.exists(file_name):
        df = pd.read_excel(file_name)
        data[user_id] = df.to_dict('records')
    else:
        data[user_id] = []


# Главные кнопки
def main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton('Добавить приход'))
    keyboard.add(types.KeyboardButton('Добавить расход'))
    keyboard.add(types.KeyboardButton('Экспорт данных'))
    keyboard.add(types.KeyboardButton('Удалить таблицу'))
    return keyboard


@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    load_data_from_file(user_id)  # Загрузка данных из файла при старте
    bot.send_message(message.chat.id, "Привет! Я помогу вести учет денежных потоков.", reply_markup=main_keyboard())


@bot.message_handler(func=lambda message: message.text == 'Добавить приход')
def add_income(message):
    msg = bot.send_message(message.chat.id, "Введите сумму прихода и источник (например, '10000 от продаж'):")
    bot.register_next_step_handler(msg, process_income)


def process_income(message):
    try:
        amount, source = message.text.split(' от ')
        user_id = message.from_user.id
        if user_id not in data:
            data[user_id] = []

        data[user_id].append({"Дата": formatted_date, "Тип": "Приход", "Сумма": float(amount), "Источник": source})
        bot.send_message(message.chat.id, "Приход добавлен!", reply_markup=main_keyboard())
    except ValueError:
        bot.send_message(message.chat.id, "Неправильный формат ввода. Попробуйте снова.", reply_markup=main_keyboard())


@bot.message_handler(func=lambda message: message.text == 'Добавить расход')
def add_expense(message):
    msg = bot.send_message(message.chat.id, "Введите сумму расхода и категорию (например, '5000 на аренду'):")
    bot.register_next_step_handler(msg, process_expense)


def process_expense(message):
    try:
        amount, category = message.text.split(' на ')
        user_id = message.from_user.id
        if user_id not in data:
            data[user_id] = []

        data[user_id].append({"Дата": formatted_date, "Тип": "Расход", "Сумма": float(amount), "Категория": category})
        bot.send_message(message.chat.id, "Расход добавлен!", reply_markup=main_keyboard())
    except ValueError:
        bot.send_message(message.chat.id, "Неправильный формат ввода. Попробуйте снова.", reply_markup=main_keyboard())


@bot.message_handler(func=lambda message: message.text == 'Экспорт данных')
def export_data(message):
    user_id = message.from_user.id
    if user_id in data and data[user_id]:
        df = pd.DataFrame(data[user_id])

        # Добавление строки с общей суммой
        total_sum = df["Сумма"].sum()
        df = pd.concat([df, pd.DataFrame([{"Тип": "Итого", "Сумма": total_sum}])], ignore_index=True)

        file_name = os.path.join(FILE_DIR, f'financial_report_{user_id}.xlsx')
        df.to_excel(file_name, index=False)

        # Удаление итоговой строки из DataFrame перед сохранением обратно в структуру данных
        df = df[df["Тип"] != "Итого"]
        data[user_id] = df.to_dict('records')

        with open(file_name, 'rb') as file:
            bot.send_document(message.chat.id, file)
    else:
        bot.send_message(message.chat.id, "Нет данных для экспорта.", reply_markup=main_keyboard())


@bot.message_handler(func=lambda message: message.text == 'Удалить таблицу')
def delete_table(message):
    user_id = message.from_user.id
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Да", callback_data="confirm_delete"))
    keyboard.add(types.InlineKeyboardButton("Нет", callback_data="cancel_delete"))
    bot.send_message(message.chat.id, "Вы уверены, что хотите удалить все данные?", reply_markup=keyboard)


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