import requests
import datetime
import pytz
import logging
import time

# Настройка логирования
logging.basicConfig(
    filename='weather_bot.log', 
    level=logging.INFO,  # Изменено на INFO для более детального логирования
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger()

# Конфигурация
TELEGRAM_BOT_TOKEN = "7409034572:AAEomEwpuKdBgJsI7BJPm-Cx-GogBsrofvQ"
TELEGRAM_CHANNEL_ID = "-1002558606938"
OPENWEATHER_API_KEY = "8c1d561d0e5214acd00561ab8ff73f77"
CITY = "Перегоричи"  # Замените на нужный город
TIMEZONE = "Europe/Moscow"  # Часовой пояс города
MAX_RETRIES = 3  # Максимальное количество попыток получения данных

def get_tomorrows_detailed_forecast():
    """Получает детальный прогноз погоды на следующий день с шагом 3 часа"""
    retries = 0
    while retries < MAX_RETRIES:
        try:
            # Получаем 5-дневный прогноз (40 периодов по 3 часа)
            url = f"http://api.openweathermap.org/data/2.5/forecast?q={CITY}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru"
            response = requests.get(url, timeout=10).json()
            
            if response.get('cod') != '200':
                error_msg = response.get('message', 'Unknown error')
                logger.error(f"OpenWeatherMap error: {error_msg}")
                return None

            # Текущее время в нужном часовом поясе
            tz = pytz.timezone(TIMEZONE)
            now = datetime.datetime.now(tz)
            tomorrow = now.date() + datetime.timedelta(days=1)
            
            # Фильтруем прогнозы на завтра
            forecasts = []
            for item in response.get('list', []):
                forecast_time = datetime.datetime.fromtimestamp(item['dt'], tz=tz)
                if forecast_time.date() == tomorrow:
                    forecasts.append({
                        'time': forecast_time,
                        'hour': forecast_time.hour,
                        'temp': item['main']['temp'],
                        'feels_like': item['main']['feels_like'],
                        'description': item['weather'][0]['description'],
                        'humidity': item['main']['humidity'],
                        'wind': item['wind']['speed'],
                        'icon': item['weather'][0]['icon'],
                        'pressure': item['main']['pressure'],
                        'clouds': item['clouds']['all']
                    })
            
            # Если не найдено прогнозов на завтра
            if not forecasts:
                logger.warning(f"No forecast found for tomorrow ({tomorrow})")
                return None
                
            # Сортируем по времени
            forecasts.sort(key=lambda x: x['time'])
            
            return {
                'date': tomorrow.strftime("%d.%m.%Y"),
                'weekday': tomorrow.strftime("%A").capitalize(),  # Добавляем день недели
                'forecasts': forecasts
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            retries += 1
            if retries < MAX_RETRIES:
                logger.info(f"Retrying... ({retries}/{MAX_RETRIES})")
                time.sleep(2)  # Задержка перед повторной попыткой
                
        except Exception as e:
            logger.exception("Unexpected error in get_tomorrows_detailed_forecast")
            return None
            
    logger.error(f"Failed to get forecast after {MAX_RETRIES} attempts")
    return None

def send_to_telegram(message):
    """Отправляет сообщение в Telegram-канал"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHANNEL_ID,
            "text": message,
            "parse_mode": "HTML",
"disable_web_page_preview": True
        }
        response = requests.post(url, json=payload, timeout=10)
        
        # Проверяем успешность отправки
        if response.status_code != 200:
            logger.error(f"Telegram API error: {response.status_code} - {response.text}")
            return False
            
        return True
        
    except Exception as e:
        logger.exception("Error in send_to_telegram")
        return False

# Иконки для разных типов погоды
WEATHER_ICONS = {
    '01d': '☀️',  # ясно (день)
    '01n': '🌙',  # ясно (ночь)
    '02d': '⛅️',  # малооблачно (день)
    '02n': '☁️🌙', # малооблачно (ночь)
    '03d': '☁️',  # облачно
    '03n': '☁️',  
    '04d': '🌥',  # пасмурно
    '04n': '🌥',  
    '09d': '🌧',  # дождь
    '09n': '🌧',  
    '10d': '🌦',  # дождь с солнцем
    '10n': '🌧',  
    '11d': '⛈',  # гроза
    '11n': '⛈',  
    '13d': '❄️',  # снег
    '13n': '❄️',  
    '50d': '🌫',  # туман
    '50n': '🌫'   
}

# Иконки для времени суток
HOUR_ICONS = {
    0: '🌙', 3: '🌙', 6: '🌅', 9: '🌤️', 
    12: '☀️', 15: '🌞', 18: '🌇', 21: '🌃'
}

def get_hour_icon(hour):
    """Возвращает иконку для времени суток"""
    for h, icon in sorted(HOUR_ICONS.items(), reverse=True):
        if hour >= h:
            return icon
    return '🕒'

# Форматирование и отправка сообщения
def main():
    logger.info("Starting weather forecast script")
    
    forecast = get_tomorrows_detailed_forecast()
    
    if not forecast:
        error_msg = "❌ Не удалось получить прогноз погоды. Попробуем снова позже."
        logger.error(error_msg)
        send_to_telegram(error_msg)
        return

    try:
        # Заголовок сообщения с днем недели
        weekday_icons = {
            "Monday": "📅 Понедельник",
            "Tuesday": "📅 Вторник",
            "Wednesday": "📅 Среда",
            "Thursday": "📅 Четверг",
            "Friday": "📅 Пятница",
            "Saturday": "🎉 Суббота",
            "Sunday": "🌟 Воскресенье"
        }
        
        weekday_icon = weekday_icons.get(forecast['weekday'], "📅")
        
        message = (
            f"<b>{weekday_icon} {forecast['weekday']}, {forecast['date']}</b>\n"
            f"📍 Прогноз погоды в <b>{CITY}</b>\n\n"
            f"<b>🕒 Время  |  🌤️ Погода  |  🌡️ Темп.  |  💨 Ветер  |  💧 Влажн.</b>\n"
            f"────────────────────────────────"
        )
        
        # Добавляем каждый 3-часовой прогноз
        for f in forecast['forecasts']:
            # Получаем иконку для погоды
            weather_icon = WEATHER_ICONS.get(f['icon'], '🌤️')
            
            # Получаем иконку для времени суток
            hour_icon = get_hour_icon(f['hour'])
            
            # Форматируем время
            time_str = f['time'].strftime("%H:%M")
            
            # Форматируем температуру (цвет в зависимости от значения)
            temp = f['temp']
            temp_color = ""
            if temp < 0:
                temp_color = "🔵"  # очень холодно
            elif temp < 10:
                temp_color = "🟦"  # холодно
            elif temp < 20:
                temp_color = "🟩"  # прохладно
            elif temp < 30:
                temp_color = "🟧"  # тепло
            else:
                temp_color = "🟥"  # жарко
                
            # Форматируем ветер
            wind = f['wind']
            wind_icon = "🍃" if wind < 1 else "💨" if wind < 5 else "🌬️"
            
            # Форматируем влажность
            humidity = f['humidity']
            humidity_icon = "💧"
            if humidity < 30:
                humidity_icon = "🏜️"
            elif humidity > 80:
                humidity_icon = "🌊"
                
            # Форматируем строку прогноза
            # Укорачиваем длинные описания погоды
            description = f['description'].capitalize()
            if len(description) > 15:
                description = description[:12] + ".."
                
            forecast_line = (
                f"\n{hour_icon} <b>{time_str}</b>  |  "
                f"{weather_icon} {description:<15} |  "
                f"{temp_color} <b>{temp}°C</b> |  "
                f"{wind_icon} <b>{wind} м/с</b> |  "
                f"{humidity_icon} <b>{humidity}%</b>"
            )
            
            message += forecast_line
        
        # Добавляем разделитель и доп. информацию
        message += "\n\n────────────────────────────────"
        
        # Добавляем сводку по дню
        try:
            temps = [f['temp'] for f in forecast['forecasts']]
            min_temp = min(temps)
            max_temp = max(temps)
            winds = [f['wind'] for f in forecast['forecasts']]
            avg_wind = round(sum(winds) / len(winds), 1)
            humidities = [f['humidity'] for f in forecast['forecasts']]
            avg_humidity = round(sum(humidities) / len(humidities))
            
            message += (
                f"\n\n<b>📊 Сводка на завтра:</b>\n"
                f"🌡️ Мин/макс: <b>{min_temp}°C</b> / <b>{max_temp}°C</b>\n"
                f"💨 Ветер: до <b>{max(winds)} м/с</b>\n"
                f"💧 Влажность: в среднем <b>{avg_humidity}%</b>"
            )
        except Exception as e:
            logger.error(f"Error in summary calculation: {e}")
        
        message += "\n\n<i>ℹ️ Температура: 🔵<0°C 🟦0-9°C 🟩10-19°C 🟧20-29°C 🟥30+°C</i>"
        message += "\n<i>ℹ️ Ветер: 🍃<1м/с 💨1-5м/с 🌬️>5м/с</i>"
        message += "\n<i>ℹ️ Влажность: 🏜️<30% 💧30-80% 🌊>80%</i>"
        message += "\n\n#погода #прогноз #завтра"
        
        # Отправляем сообщение
        success = send_to_telegram(message)
        if success:
            logger.info("Forecast sent successfully")
        else:
            logger.error("Failed to send forecast")
            
    except Exception as e:
        logger.exception("Error in main processing")
        send_to_telegram("❌ Ошибка при формировании прогноза погоды")

if __name__ == "__main__":
    main()