import telebot
from datetime import datetime
from telebot import types
import pandas as pd

now = datetime.now()
formatted_date = now.strftime('%d-%m-%Y')
API_TOKEN = '7281044136:AAGwoyl2iVDfvvo_y6Qe64oW8mFv4AE4WL4'

bot = telebot.TeleBot(API_TOKEN)

# Хранение данных о транзакциях
data = {}


# Главные кнопки
def main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton('Добавить приход'))
    keyboard.add(types.KeyboardButton('Добавить расход'))
    keyboard.add(types.KeyboardButton('Экспорт данных'))
    return keyboard


@bot.message_handler(commands=['start'])
def start(message):
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
        bot.send_message(message.chat.id, "Приход добавлен", reply_markup=main_keyboard())
    except ValueError:
        bot.send_message(message.chat.id, "Неправильный формат ввода. Попробуйте снова.", reply_markup=main_keyboard())


@bot.message_handler(func=lambda message: message.text == 'Добавить расход')
def add_expense(message):
    msg = bot.send_message(message.chat.id, "Введите сумму расхода и категорию (например, '-5000 на аренду'):")
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
    if user_id in data:
        df = pd.DataFrame(data[user_id])

        # Добавление строки с общей суммой
        total_sum = df["Сумма"].sum()
        df = pd.concat([df, pd.DataFrame([{"Тип": "Прибыль", "Сумма": total_sum}])], ignore_index=True)

        file_name = f'financial_report_{user_id}.xlsx'
        df.to_excel(file_name, index=False)

        # Удаление итоговой строки из DataFrame перед сохранением обратно в бд
        df = df[df["Тип"] != "Прибыль"]
        data[user_id] = df.to_dict('records')

        with open(file_name, 'rb') as file:
            bot.send_document(message.chat.id, file)
    else:
        bot.send_message(message.chat.id, "Нет данных для экспорта.", reply_markup=main_keyboard())


if __name__ == '__main__':
    bot.polling(none_stop=True)
