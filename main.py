import telebot
import requests
import json
import sqlite3
from datetime import datetime, timedelta
from telebot.types import BotCommand

# Ваш токен OpenWeatherMap API
API = '9c4aa55e3c591876ee4e5ed396a3d470'
# Токен Telegram-бота
bot = telebot.TeleBot('7639076031:AAGKA7X-5rE7VrW-qP-YRse95WjlaLV49dc')

# Підключення до бази даних SQLite
conn = sqlite3.connect('weather_bot.db', check_same_thread=False)
cursor = conn.cursor()

# Створення таблиці для збереження історії запитів
cursor.execute('''
    CREATE TABLE IF NOT EXISTS weather_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        city TEXT,
        request_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
conn.commit()

# Установка глобального меню команд
commands = [
    BotCommand("start", "Запустити бота"),
    BotCommand("help", "Довідка про використання"),
    BotCommand("history", "Переглянути історію запитів")
]
bot.set_my_commands(commands)

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(
        message.chat.id,
        'Привіт! Введи назву міста, щоб дізнатися прогноз погоди або скористайся командами з меню.'
    )

@bot.message_handler(commands=['help'])
def help_message(message):
    bot.send_message(
        message.chat.id,
        "Команди бота:\n"
        "/start - Запустити бота\n"
        "/help - Довідка\n"
        "/history - Переглянути історію запитів\n"
        "Введи назву міста, щоб отримати прогноз погоди."
    )

@bot.message_handler(commands=['history'])
def show_history(message):
    user_id = message.from_user.id

    # Отримання історії запитів
    cursor.execute(
        "SELECT city, request_time FROM weather_requests WHERE user_id = ? ORDER BY request_time DESC",
        (user_id,)
    )
    history = cursor.fetchall()

    if history:
        response = "Історія ваших запитів:\n"
        for city, time in history:
            response += f"{city.capitalize()} - {time}\n"
    else:
        response = "У вас ще немає запитів."

    bot.send_message(message.chat.id, response)

@bot.message_handler(content_types=['text'])
def get_weather(message):
    city = message.text.strip().lower()
    user_id = message.from_user.id

    try:
        # Збереження запиту в базу
        cursor.execute(
            "INSERT INTO weather_requests (user_id, city) VALUES (?, ?)",
            (user_id, city)
        )
        conn.commit()

        # Запрос до OpenWeatherMap API
        res = requests.get(f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API}&units=metric')
        data = json.loads(res.text)

        if res.status_code == 200:
            # Дані про погоду
            temp = data['main']['temp']
            description = data['weather'][0]['description']
            humidity = data['main']['humidity']
            pressure = data['main']['pressure']
            wind_speed = data['wind']['speed']
            sunrise = data['sys']['sunrise']
            sunset = data['sys']['sunset']
            current_time = data['dt']
            timezone_offset = data['timezone']

            # Конвертуємо час у місцевий (з урахуванням часового зсуву)
            current_time_dt = datetime.utcfromtimestamp(current_time) + timedelta(seconds=timezone_offset)
            sunrise_time = datetime.utcfromtimestamp(sunrise) + timedelta(seconds=timezone_offset)
            sunset_time = datetime.utcfromtimestamp(sunset) + timedelta(seconds=timezone_offset)

            # Логіка вибору зображення
            if 'rain' in description.lower():
                image = './rain.jpg'
            elif 'snow' in description.lower():
                image = './snow.jpg'
            elif sunrise_time <= current_time_dt <= sunset_time:
                image = './sunny.jpg' if temp > 10.0 else './cloudy.jpg'
            else:
                image = './night.jpg'

            # Відправляємо повідомлення з погодою
            bot.reply_to(
                message,
                f"Погода в {city.capitalize()}:\n"
                f"Температура: {temp}°C\n"
                f"Опис: {description.capitalize()}\n"
                f"Вологість: {humidity}%\n"
                f"Тиск: {pressure} hPa\n"
                f"Швидкість вітру: {wind_speed} м/с\n"
                f"Час: {current_time_dt.strftime('%d-%m-%Y %H:%M:%S')}\n"
                f"Схід сонця: {sunrise_time.strftime('%d-%m-%Y %H:%M:%S')}\n"
                f"Захід сонця: {sunset_time.strftime('%d-%m-%Y %H:%M:%S')}"
            )

            # Відправляємо зображення
            with open(image, 'rb') as img:
                bot.send_photo(message.chat.id, img)
        else:
            bot.reply_to(message, f"Місто \"{city}\" не знайдено. Спробуйте ще раз.")
    except Exception as e:
        bot.reply_to(message, f"Сталася помилка: {e}")

bot.polling(none_stop=True)
