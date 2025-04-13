import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from datetime import datetime, timedelta
import re
import pymysql
import pymysql.cursors
import cv2
import threading
import time
from random import randint

bot = telebot.TeleBot("7866686310:AAGx0OR3Zl8iYflOKRGAT6TIQM3_4g01-RE")

# Словарь для русификации дней недели
rus_weekdays = {
    'Mon': 'Пн', 'Tue': 'Вт', 'Wed': 'Ср', 
    'Thu': 'Чт', 'Fri': 'Пт', 'Sat': 'Сб', 'Sun': 'Вс'
}

# Словарь свободных слотов
freeDict = {
    '1': '1', '2': '1', '3': '1', '4': '1', '5': '1',
    '6': '1', '7': '1', '8': '1', '9': '1', '10': '1',
    '11': '1', '12': '1', '13': '1', '14': '1'
}

# Хранилище данных пользователей
user_data = {}

def check_ban(connection, id):
    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT banned FROM `titanit`.`users`
            WHERE `user_id` = {id}
        """)
        return cursor.fetchone()['banned'] == 1

def check_upcoming_bookings():
    """Проверяет предстоящие брони и отправляет напоминания, а также проверяет пропущенные брони"""
    while True:
        try:
            connection = pymysql.connect(
                host="127.0.0.1",
                port=3308,
                user="root",
                password="root",
                database="titanit",
                cursorclass=pymysql.cursors.DictCursor
            )
            
            now = datetime.now()
            reminder_time = (now + timedelta(hours=1)).strftime("%d.%m.%Y %H:%M")
            current_time_str = now.strftime("%d.%m.%Y %H:%M")
            
            with connection.cursor() as cursor:
                # 1. Проверка предстоящих броней для напоминаний
                cursor.execute(f"""
                    SELECT * FROM `titanit`.`busytable`
                    WHERE STR_TO_DATE(CONCAT(`cur_date`, ' ', `start_time`), '%d.%m.%Y %H:%i') 
                    BETWEEN STR_TO_DATE('{current_time_str}', '%d.%m.%Y %H:%i') 
                    AND STR_TO_DATE('{reminder_time}', '%d.%m.%Y %H:%i')
                    AND `reminder_sent` = 0
                """)
                bookings = cursor.fetchall()
                
                for booking in bookings:
                    try:
                        bot.send_message(
                            booking['user_id'],
                            f"⏰ Напоминание: у вас бронь через 1 час!\n\n"
                            f"📅 Дата: {booking['cur_date']}\n"
                            f"⏰ Время: {booking['start_time']}-{booking['end_time']}\n"
                            f"📍 Место: {booking['place']}",
                            reply_markup=ReplyKeyboardMarkup(resize_keyboard=True)
                            .add(KeyboardButton("Мои брони")))
                        
                        # Помечаем, что напоминание отправлено
                        cursor.execute(f"""
                            UPDATE `titanit`.`busytable`
                            SET `reminder_sent` = 1
                            WHERE `id` = {booking['id']}
                        """)
                        connection.commit()
                        
                    except Exception as e:
                        print(f"Ошибка при отправке напоминания: {e}")
                        continue
                
                # 2. Проверка пропущенных броней (где end_time уже прошло, а check_in = 0)
                cursor.execute(f"""
                    SELECT b.*, u.warn, u.banned 
                    FROM `titanit`.`busytable` b
                    JOIN `titanit`.`users` u ON b.user_id = u.user_id
                    WHERE STR_TO_DATE(CONCAT(b.`cur_date`, ' ', b.`end_time`), '%d.%m.%Y %H:%i') < STR_TO_DATE('{current_time_str}', '%d.%m.%Y %H:%i')
                    AND b.`check_in` = 0
                """)
                missed_bookings = cursor.fetchall()
                cursor.execute(f"""
                    DELETE FROM `titanit`.`busytable`
                    WHERE STR_TO_DATE(CONCAT(`cur_date`, ' ', `end_time`), '%d.%m.%Y %H:%i') < STR_TO_DATE('{current_time_str}', '%d.%m.%Y %H:%i')
                    AND `check_in` = 0
                """)

                for booking in missed_bookings:
                    try:
                        user_id = booking['user_id']
                        current_warns = booking['warn']
                        is_banned = booking['banned']
                        
                        if current_warns < 2:
                            # Увеличиваем количество предупреждений
                            new_warns = current_warns + 1
                            cursor.execute(f"""
                                UPDATE `titanit`.`users`
                                SET `warn` = {new_warns}
                                WHERE `user_id` = {user_id}
                            """)
                            
                            connection.commit()
                            
                            # Уведомляем пользователя
                            bot.send_message(
                                user_id,
                                f"⚠️ Вы пропустили бронь!\n"
                                f"📅 Дата: {booking['cur_date']}\n"
                                f"⏰ Время: {booking['start_time']}-{booking['end_time']}\n"
                                f"📍 Место: {booking['place']}\n\n"
                                f"Теперь у вас {new_warns}/3 предупреждений. При получении 3 предупреждений вы будете заблокированы.",
                                reply_markup=ReplyKeyboardMarkup(resize_keyboard=True)
                                .add(KeyboardButton("Мои брони")))
                            
                        elif current_warns >= 2 and not is_banned:
                            # Блокируем пользователя
                            cursor.execute(f"""
                                UPDATE `titanit`.`users`
                                SET `warn` = 3,
                                    `banned` = 1
                                WHERE `user_id` = {user_id}
                            """)
                            
                            connection.commit()
                            
                            # Уведомляем о блокировке
                            try:
                                bot.send_message(
                                    user_id,
                                    "❌ Вы получили 3 предупреждения и были заблокированы!",
                                    reply_markup=ReplyKeyboardRemove())
                            except Exception as e:
                                print(f"Ошибка при блокировке пользователя: {e}")
                            
                    except Exception as e:
                        print(f"Ошибка при обработке пропущенной брони: {e}")
                        continue
            
        except Exception as e:
            print(f"Ошибка при проверке броней: {e}")
        finally:
            if 'connection' in locals():
                connection.close()
        
        time.sleep(60)

def draw_numbers(koord, n, image, font, fontScale, color, thickness):
    cv2.putText(image, n, koord, font, fontScale, color, thickness, cv2.LINE_AA)

def paint(freeDict, orangePlaces, favPlace):
    image = cv2.imread('banket.jpg')
    font = cv2.FONT_HERSHEY_SIMPLEX
    fontScale = 1
    color = (0, 0, 0)
    thickness = 2

    koord_arr = [(166, 240),
                (246, 240),
                (326, 240),
                (584, 158),
                (688, 158),
                (792, 158),
                (894, 158),
                (998, 158),
                (1090, 370),
                (570, 588),
                (674, 588),
                (778, 588),
                (880, 588),
                (984, 588),
                ]

    zaliv_arr = [
        [(153, 251), (199, 203)],
        [(233,251), (280,203)],
        [(313,251), (359,203)],
        [(566, 92), (621, 195)],
        [(670,93), (725,195)],
        [(774,94), (829,197)],
        [(877,95), (931,198)],
        [(979,97), (1034,200)],
        [(1068,211), (1130,521)],
        [(566,533), (621,636)],
        
        [(670,530), (725,634)],
        [(774,530), (829,632)],
        [(877,529), (931, 632)],
        [(979, 528), (1034,630)],
    ]

    for n in range(1, 15):
        if str(n) in freeDict:
            if str(n) == favPlace:
                cv2.rectangle(image, zaliv_arr[n-1][0], zaliv_arr[n-1][1], (0, 255, 255), cv2.FILLED)
        else:
            if str(n) in orangePlaces:
                cv2.rectangle(image, zaliv_arr[n-1][0], zaliv_arr[n-1][1], (55, 96, 255), cv2.FILLED)
            else:
                cv2.rectangle(image, zaliv_arr[n-1][0], zaliv_arr[n-1][1], (0, 0, 255), cv2.FILLED)
        draw_numbers(koord_arr[n-1], str(n), image, font, fontScale, color, thickness)
    cv2.imwrite('img.jpg', image)

def generate_work_dates():
    """Генерирует список рабочих дат (пн-пт) на 7 дней вперёд с русскими днями недели"""
    dates = []
    today = datetime.now().date()
    for delta in range(8):  # Сегодня + 7 дней
        date = today + timedelta(days=delta)
        if date.weekday() not in [2,3]:  # 0-4 = пн-пт
            weekday_en = date.strftime("%a")
            weekday_ru = rus_weekdays.get(weekday_en, weekday_en)
            date_str = f"{date.strftime('%d.%m.%Y')} ({weekday_ru})"
            dates.append((date_str, date.strftime("%d.%m.%Y")))
    return dates

def is_today_selected(selected_date_str):
    """Проверяет, выбрана ли сегодняшняя дата"""
    today_str = datetime.now().strftime("%d.%m.%Y")
    return selected_date_str == today_str

def get_current_time():
    """Возвращает текущее время в формате ЧЧ:ММ"""
    return datetime.now().strftime("%H:%M")

def is_working_hours_over():
    """Проверяет, закончился ли рабочий день (после 21:00)"""
    now = datetime.now()
    return now.hour >= 21

def get_available_places(selected_date, start_time, end_time, user_id):
    """
    Возвращает список свободных мест на указанное время и дату
    """
    connection = pymysql.connect(
        host="127.0.0.1",
        port=3308,
        user="root",
        password="root",
        database="titanit",
        cursorclass=pymysql.cursors.DictCursor
    )
    
    with connection.cursor() as cursor:
        # Получаем все забронированные места на эту дату и время
        cursor.execute(f"""
            SELECT `place` FROM `titanit`.`busytable`
            WHERE `cur_date` = '{selected_date}'
            AND (
                ((`start_time` <= '{end_time}' AND '{end_time}' <= `end_time`) OR (`end_time` >= '{start_time}' and '{start_time}' >= `start_time`) OR (`start_time` <= '{start_time}' AND `end_time` >= '{end_time}') OR (`start_time` >= '{start_time}' AND `end_time` <= '{end_time}'))
            )
        """)
        booked_places = [str(row['place']) for row in cursor.fetchall()]
        
        cursor.execute(f"""
            SELECT `place` FROM `titanit`.`busytable`
            WHERE `cur_date` = '{selected_date}'
            AND `end_time` <= ADDTIME('{start_time}', '00:15:00')
            AND `end_time` >= '{start_time}'
        """)

        orange_places = [str(row['place']) for row in cursor.fetchall()]

        cursor.execute(f"""SELECT place, COUNT(*) AS booking_count FROM `titanit`.`busytable` WHERE check_in = 1 AND user_id = '{user_id}'
        GROUP BY place ORDER BY booking_count DESC LIMIT 1;""")
        rr = cursor.fetchone()
        fav_place = str(rr['place'] if rr else 0)

        # Все возможные места (из freeDict)
        all_places = list(freeDict.keys())
        
        # Свободные места = все места минус забронированные, где значение '1' в freeDict
        available_places = [
            place for place in all_places 
            if place not in booked_places and freeDict.get(place) == '1'
        ]
        connection.close()
        return available_places, orange_places, fav_place

def validate_time(time_str, min_hour=9, max_hour=21, after_time=None):
    """Проверяет время и возвращает нормализованный формат (без ведущего нуля)"""
    if not re.match(r'^([01]?[0-9]|2[0-1]):([0-5][0-9])$', time_str):
        return None
    
    if time_str.startswith('0'):
        time_str = time_str[1:]
    
    hours, minutes = map(int, time_str.split(':'))
    
    if hours < min_hour or hours > max_hour or (hours == max_hour and minutes > 0):
        return None
    
    if after_time:
        after_h, after_m = map(int, after_time.split(':'))
        if hours < after_h or (hours == after_h and minutes <= after_m):
            return None
    
    return f"{hours}:{minutes:02d}"

@bot.message_handler(commands=['start'])
def start(message):
    connection = pymysql.connect(host="127.0.0.1", port=3308, user="root", password="root", database="titanit", cursorclass=pymysql.cursors.DictCursor)
    with connection.cursor() as cursor:
            cursor.execute(f"""
                SELECT * FROM `titanit`.`users` 
                WHERE `user_id` = {message.from_user.id}
            """)
            if not cursor.fetchone():
                cursor.execute(f"""
                    INSERT INTO `titanit`.`users` 
                    (`user_id`, `username`, `warn`, `banned`) 
                    VALUES (
                        '{message.from_user.id}', 
                        '{message.from_user.username}', 
                        '0', '0'
                    )
                """)
                connection.commit()
    if check_ban(connection, message.from_user.id):
        bot.send_message(message.chat.id, 'Вы забанены, по поводу разблокировки напишите администратору: @fname0')
        connection.close()
        return

    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("Выбрать дату"), KeyboardButton("Мои брони"))
    bot.send_message(
        message.chat.id,
        "Привет! С помощью меня Вы можете забронировать место в офисе.\n"
        "- *Выбрать дату* - для новой брони\n"
        "- *Мои брони* - для просмотра ваших бронирований",
        reply_markup=markup,
        parse_mode="Markdown"
    )
    connection.close()


@bot.message_handler(func=lambda m: m.text == "Выбрать дату")
def show_dates(message):
    connection = pymysql.connect(host="127.0.0.1", port=3308, user="root", password="root", database="titanit", cursorclass=pymysql.cursors.DictCursor)
    if check_ban(connection, message.from_user.id):
        bot.send_message(message.chat.id, 'Вы забанены, по поводу разблокировки напишите администратору: @fname0')
        connection.close()
        return

    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    dates = generate_work_dates()
    
    buttons = [KeyboardButton(date_str) for date_str, _ in dates]
    for i in range(0, len(buttons), 2):
        row = buttons[i:i+2]
        markup.add(*row)
    
    markup.add(KeyboardButton("Назад"))
    
    bot.send_message(
        message.chat.id,
        "Выберите рабочий день (пт-пн):",
        reply_markup=markup
    )

@bot.message_handler(func=lambda m: m.text == "Назад")
def back_handler(message):
    connection = pymysql.connect(host="127.0.0.1", port=3308, user="root", password="root", database="titanit", cursorclass=pymysql.cursors.DictCursor)
    if check_ban(connection, message.from_user.id):
        bot.send_message(message.chat.id, 'Вы забанены, по поводу разблокировки напишите администратору: @fname0')
        connection.close()
        return

    start(message=message)

@bot.message_handler(func=lambda m: any(m.text.startswith(d[0]) for d in generate_work_dates()))
def handle_date_selection(message):
    connection = pymysql.connect(host="127.0.0.1", port=3308, user="root", password="root", database="titanit", cursorclass=pymysql.cursors.DictCursor)
    if check_ban(connection, message.from_user.id):
        bot.send_message(message.chat.id, 'Вы забанены, по поводу разблокировки напишите администратору: @fname0')
        connection.close()
        return

    date_str = message.text.split()[0]
    user_data[message.chat.id] = {'date': date_str}
    
    if is_today_selected(date_str) and is_working_hours_over():
        bot.send_message(
            message.chat.id,
            "❌ Сегодня рабочий день закончен, выберите другую дату",
            reply_markup=ReplyKeyboardMarkup(resize_keyboard=True)
            .add(KeyboardButton("Выбрать дату")))
        return
    
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("Назад"))
    
    if is_today_selected(date_str):
        current_time = get_current_time()
        current_hour = datetime.now().hour
        
        if current_hour < 9:  # Если сейчас раньше 9:00
            bot.send_message(
                message.chat.id,
                f"Выбрана дата: *{date_str}*\nРабочий день начинается в 09:00. "
                f"Введите время начала в формате *ЧЧ:MM* (09:00-21:00):",
                reply_markup=markup,
                parse_mode="Markdown"
            )
        else:
            bot.send_message(
                message.chat.id,
                f"Выбрана дата: *{date_str}*\nВведите время начала в формате *ЧЧ:MM* (от {current_time} до 21:00):",
                reply_markup=markup,
                parse_mode="Markdown"
            )
    else:
        bot.send_message(
            message.chat.id,
            f"Выбрана дата: *{date_str}*\nВведите время начала в формате *ЧЧ:MM* (09:00-21:00):",
            reply_markup=markup,
            parse_mode="Markdown"
        )

@bot.message_handler(func=lambda m: m.text == "Мои брони")
def show_user_bookings(message):
    connection = pymysql.connect(host="127.0.0.1", port=3308, user="root", password="root", database="titanit", cursorclass=pymysql.cursors.DictCursor)
    if check_ban(connection, message.from_user.id):
        bot.send_message(message.chat.id, 'Вы забанены, по поводу разблокировки напишите администратору: @fname0')
        connection.close()
        return
        
    current_datetime = datetime.now().strftime("%d.%m.%Y %H:%M")
    
    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT * FROM `titanit`.`busytable` 
            WHERE `user_id` = {message.from_user.id} 
            AND STR_TO_DATE(CONCAT(`cur_date`, ' ', `end_time`), '%d.%m.%Y %H:%i') > STR_TO_DATE('{current_datetime}', '%d.%m.%Y %H:%i')
            ORDER BY `cur_date`, `start_time`
        """)
        bookings = cursor.fetchall()
    
    if not bookings:
        bot.send_message(
            message.chat.id,
            "У вас нет активных бронирований.",
            reply_markup=ReplyKeyboardMarkup(resize_keyboard=True)
            .add(KeyboardButton("Выбрать дату"), KeyboardButton("Мои брони")))
        return
    
    current_bookings = []
    future_bookings = []
    
    for booking in bookings:
        booking_start = datetime.strptime(f"{booking['cur_date']} {booking['start_time']}", "%d.%m.%Y %H:%M")
        booking_end = datetime.strptime(f"{booking['cur_date']} {booking['end_time']}", "%d.%m.%Y %H:%M")
        now = datetime.now()
        
        if booking_start <= now <= booking_end:
            current_bookings.append(booking)
        else:
            future_bookings.append(booking)
    
    response = ""
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    
    if current_bookings:
        response += f"⏳ *Текущие бронирования( {'чек-ин' if current_bookings[0]['check_in'] == 0 else 'чек-аут'} ):*\n\n"
        for booking in current_bookings:
            btn_text = f"{booking['cur_date']} {booking['start_time']}-{booking['end_time']}"
            markup.add(KeyboardButton(btn_text))
            response += (
                f"📍 Место: {booking['place']}\n"
                f"📅 Дата: {booking['cur_date']}\n"
                f"⏱ Время: {booking['start_time']} - {booking['end_time']}\n"
                f"----------------\n"
            )
    
    if future_bookings:
        response += "\n📅 *Будущие бронирования( отменить ):*\n\n"
        for booking in future_bookings:
            btn_text = f"{booking['cur_date']} {booking['start_time']}-{booking['end_time']}"
            markup.add(KeyboardButton(btn_text))
            response += (
                f"📍 Место: {booking['place']}\n"
                f"📅 Дата: {booking['cur_date']}\n"
                f"⏱ Время: {booking['start_time']} - {booking['end_time']}\n"
                f"----------------\n"
            )
    
    markup.add(KeyboardButton("Назад"))
    
    bot.send_message(
        message.chat.id,
        response,
        parse_mode="Markdown",
        reply_markup=markup
    )
    
    user_data[message.chat.id] = {
        'bookings': {
            f"{b['cur_date']} {b['start_time']}-{b['end_time']}": b for b in bookings
        }
    }
    connection.close()

@bot.message_handler(func=lambda m: m.text and any(
    b['cur_date'] + ' ' + b['start_time'] + '-' + b['end_time'] == m.text
    for b in user_data.get(m.chat.id, {}).get('bookings', {}).values()
))
def handle_booking_selection(message):
    connection = pymysql.connect(host="127.0.0.1", port=3308, user="root", password="root", database="titanit", cursorclass=pymysql.cursors.DictCursor)
    if check_ban(connection, message.from_user.id):
        bot.send_message(message.chat.id, 'Вы забанены, по поводу разблокировки напишите администратору: @fname0')
        connection.close()
        return
    connection.close()

    booking_info = user_data[message.chat.id]['bookings'][message.text]
    booking_start = datetime.strptime(f"{booking_info['cur_date']} {booking_info['start_time']}", "%d.%m.%Y %H:%M")
    booking_end = datetime.strptime(f"{booking_info['cur_date']} {booking_info['end_time']}", "%d.%m.%Y %H:%M")
    now = datetime.now()
    
    if booking_start <= now <= booking_end and booking_info['check_in'] == 0:
        msg = bot.send_message(
            message.chat.id,
            "Это текущая бронь. Введите код с экрана для чек-ина:",
            reply_markup=ReplyKeyboardMarkup(resize_keyboard=True)
            .add(KeyboardButton("Назад")))
        
        user_data[message.chat.id]['current_booking'] = booking_info
        bot.register_next_step_handler(msg, verify_booking_code)
    elif booking_start <= now <= booking_end:
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(KeyboardButton("Да"), KeyboardButton("Нет"))
        
        msg = bot.send_message(
            message.chat.id,
            "Вы хотите завершить бронирование?",
            reply_markup=markup)
        
        user_data[message.chat.id]['checkout_booking'] = booking_info
        bot.register_next_step_handler(msg, confirm_checkout)
    else:
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(KeyboardButton("Да"), KeyboardButton("Нет"))
        
        msg = bot.send_message(
            message.chat.id,
            f"Вы действительно хотите отменить бронь на {message.text}?",
            reply_markup=markup)
        
        user_data[message.chat.id]['future_booking'] = booking_info
        bot.register_next_step_handler(msg, confirm_future_booking_cancel)

def confirm_checkout(message):
    if message.text == "Да":
        booking_info = user_data[message.chat.id]['checkout_booking']
        current_time = datetime.now().strftime("%H:%M")
        
        connection = pymysql.connect(
            host="127.0.0.1", 
            port=3308, 
            user="root", 
            password="root", 
            database="titanit", 
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with connection.cursor() as cursor:
            cursor.execute(f"""
                UPDATE `titanit`.`busytable`
                SET `end_time` = '{current_time}'
                WHERE `id` = {booking_info['id']}
            """)
        connection.commit()
        
        msg = bot.send_message(message.chat.id,"✅ Чек-аут успешно выполнен! Хотите оставить отзыв о рабочем месте или офисе в целом?",reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("Хочу"), KeyboardButton("Не хочу")))
        
        bot.register_next_step_handler(msg, check_comment)

        if 'connection' in locals():
            connection.close()
    else:
        show_user_bookings(message)

def check_comment(message):
    if message.text == 'Хочу':
        msg = bot.send_message(message.chat.id,"Прекрасно! Оставьте своё мнение, пожелание или жалобу относительно рабочего места или офиса в целом",reply_markup=ReplyKeyboardRemove())
    
        bot.register_next_step_handler(msg, save_text)
    else:
        bot.send_message(message.chat.id,"Ок",reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("Выбрать дату"), KeyboardButton("Мои брони")))

def save_text(message):
    user_data[message.chat.id]['comm_text'] = message.text
    msg = bot.send_message(message.chat.id,"Теперь выберите оценку от 1 до 5",reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton('⭐⭐⭐⭐⭐'), KeyboardButton('⭐⭐⭐⭐'), KeyboardButton('⭐⭐⭐'), KeyboardButton('⭐⭐'), KeyboardButton('⭐')))
    
    bot.register_next_step_handler(msg, save_comment)

def save_comment(message):
    connection = pymysql.connect(
        host="127.0.0.1", 
        port=3308, 
        user="root", 
        password="root", 
        database="titanit", 
        cursorclass=pymysql.cursors.DictCursor
    )
    with connection.cursor() as cursor:
        cursor.execute(f"""
            INSERT INTO `titanit`.`comm` 
                (`user_id`, `username`, `place`, `cur_date`, `cur_time`, `txt`, `score`) 
                VALUES (
                    '{message.from_user.id}', 
                    '{message.from_user.username}', 
                    '{user_data[message.chat.id]['checkout_booking']['place']}',
                    '{datetime.now().strftime('%d.%m.%Y')}',
                    '{datetime.now().strftime('%H:%M')}',
                    '{user_data[message.chat.id]['comm_text']}', 
                    '{message.text.count('⭐')}'
                )
        """)
    connection.commit()
    connection.close()

    bot.send_message(message.chat.id,"Спасибо за обратную связь! ❤️ В случае необходимости с Вами свяжется администратор",reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("Выбрать дату"), KeyboardButton("Мои брони")))
    



def verify_booking_code(message):
    if message.text == "Назад":
        show_user_bookings(message)
        return
    
    if message.text == str(user_data[message.chat.id]['current_booking']['prufcode']):
        try:
            booking_info = user_data[message.chat.id]['current_booking']
            connection = pymysql.connect(
                host="127.0.0.1", 
                port=3308, 
                user="root", 
                password="root", 
                database="titanit", 
                cursorclass=pymysql.cursors.DictCursor
            )
            
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    UPDATE `titanit`.`busytable` 
                    SET `check_in` = '1'
                    WHERE `user_id` = '{message.from_user.id}'
                    AND `cur_date` = '{booking_info['cur_date']}'
                    AND `start_time` = '{booking_info['start_time']}'
                    AND `end_time` = '{booking_info['end_time']}'
                """)
            connection.commit()

            bot.send_message(
                message.chat.id,
                "✅ Чек-ин успешно пройден!",
                reply_markup=ReplyKeyboardMarkup(resize_keyboard=True)
                .add(KeyboardButton("Выбрать дату"), KeyboardButton("Мои брони")))
        
        except Exception as e:
            bot.send_message(
                message.chat.id,
                f"Ошибка при отмене брони: {str(e)}",
                reply_markup=ReplyKeyboardMarkup(resize_keyboard=True)
                .add(KeyboardButton("Выбрать дату"), KeyboardButton("Мои брони")))
        finally:
            if 'connection' in locals():
                connection.close()
    else:
        bot.send_message(
            message.chat.id,
            "❌ Неверный код! Попробуйте еще раз или нажмите 'Назад'",
            reply_markup=ReplyKeyboardMarkup(resize_keyboard=True)
            .add(KeyboardButton("Назад")))
        bot.register_next_step_handler(message, verify_booking_code)

def confirm_future_booking_cancel(message):
    if message.text == "Да":
        try:
            booking_info = user_data[message.chat.id]['future_booking']
            connection = pymysql.connect(
                host="127.0.0.1", 
                port=3308, 
                user="root", 
                password="root", 
                database="titanit", 
                cursorclass=pymysql.cursors.DictCursor
            )
            
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    DELETE FROM `titanit`.`busytable` 
                    WHERE `user_id` = {message.from_user.id}
                    AND `cur_date` = '{booking_info['cur_date']}'
                    AND `start_time` = '{booking_info['start_time']}'
                    AND `end_time` = '{booking_info['end_time']}'
                """)
            connection.commit()
            
            bot.send_message(
                message.chat.id,
                "✅ Бронь успешно отменена!",
                reply_markup=ReplyKeyboardMarkup(resize_keyboard=True)
                .add(KeyboardButton("Выбрать дату"), KeyboardButton("Мои брони")))
        
        except Exception as e:
            bot.send_message(
                message.chat.id,
                f"Ошибка при отмене брони: {str(e)}",
                reply_markup=ReplyKeyboardMarkup(resize_keyboard=True)
                .add(KeyboardButton("Выбрать дату"), KeyboardButton("Мои брони")))
        finally:
            if 'connection' in locals():
                connection.close()
    else:
        show_user_bookings(message)

@bot.message_handler(func=lambda m: True)
def handle_time_input(message):
    connection = pymysql.connect(host="127.0.0.1", port=3308, user="root", password="root", database="titanit", cursorclass=pymysql.cursors.DictCursor)
    if check_ban(connection, message.from_user.id):
        bot.send_message(message.chat.id, 'Вы забанены, по поводу разблокировки напишите администратору: @fname0')
        connection.close()
        return

    user_id = message.chat.id
    if user_id not in user_data or 'date' not in user_data[user_id]:
        return
    
    if message.text == "Назад":
        back_handler(message)
        return
    
    # Обработка подтверждения/отмены бронирования
    if 'place' in user_data[user_id] and message.text in ["Подтвердить", "Отменить"]:
        if message.text == "Подтвердить":
            # Сохраняем бронирование в БД
            date_str = user_data[user_id]['date']
            start_time = user_data[user_id]['start_time']
            end_time = user_data[user_id]['end_time']
            place = user_data[user_id]['place']
            prufcode = randint(111111, 999999)

            booking_datetime = datetime.strptime(f"{date_str} {start_time}", "%d.%m.%Y %H:%M")
            time_until_booking = (booking_datetime - datetime.now()).total_seconds() / 60
            
            reminder_sent = 1 if time_until_booking <= 60 else 0
                
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    INSERT INTO `titanit`.`busytable` 
                    (`user_id`, `username`, `place`, `cur_date`, `start_time`, `end_time`, `reminder_sent`, `prufcode`) 
                    VALUES (
                        '{message.from_user.id}', 
                        '{message.from_user.username}', 
                        '{place}', 
                        '{date_str}', 
                        '{start_time}', 
                        '{end_time}',
                        '{reminder_sent}',
                        '{prufcode}'
                    )
                """)
            connection.commit()
            
            bot.send_message(
                message.chat.id,
                f"✅ Бронирование подтверждено!\n\n"
                f"📅 Дата: *{date_str}*\n"
                f"⏰ Время: *{start_time} - {end_time}*\n"
                f"📍 Место: *{place}*",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardMarkup(resize_keyboard=True)
                .add(KeyboardButton("Выбрать дату"), KeyboardButton("Мои брони")))
            connection.close()
        else:
            # Отмена бронирования
            bot.send_message(
                message.chat.id,
                "❌ Бронирование отменено",
                reply_markup=ReplyKeyboardMarkup(resize_keyboard=True)
                .add(KeyboardButton("Выбрать дату"), KeyboardButton("Мои брони")))
        
        # Очищаем данные пользователя
        if user_id in user_data:
            del user_data[user_id]
        return
    
    if 'start_time' not in user_data[user_id]:
        date_str = user_data[user_id]['date']
        
        min_hour = 9
        if is_today_selected(date_str):
            current_time = get_current_time()
            start_time = validate_time(message.text, min_hour=9, max_hour=21, after_time=current_time)
        else:
            start_time = validate_time(message.text, min_hour=9, max_hour=21)
        
        if not start_time:
            bot.reply_to(message, "❌ Некорректное время! Пожалуйста, введите время в правильном формате и диапазоне.")
            return
        
        if len(start_time.split(':')[0]) == 1:
            start_time = f"0{start_time}"

        user_data[user_id]['start_time'] = start_time
        
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(KeyboardButton("Назад"))
        
        bot.send_message(
            message.chat.id,
            f"Введено время начала: *{start_time}*\nВведите время окончания в формате *ЧЧ:MM* (от {start_time} до 21:00):",
            reply_markup=markup,
            parse_mode="Markdown"
        )
    
    elif 'end_time' not in user_data[user_id]:
        start_time = user_data[user_id]['start_time']
        end_time = validate_time(message.text, min_hour=9, max_hour=21, after_time=start_time)
        
        if not end_time:
            bot.reply_to(message, f"❌ Время окончания должно быть после {start_time} и до 21:00!")
            return
        
        if len(end_time.split(':')[0]) == 1:
            end_time = f"0{end_time}"
        
        user_data[user_id]['end_time'] = end_time
        
        # Получаем доступные места для выбранного времени
        date_str = user_data[user_id]['date']
        available_places, orange_places, fav_place = get_available_places(date_str, start_time, end_time, message.from_user.id)
        
        if not available_places:
            bot.send_message(
                message.chat.id,
                "❌ На выбранное время нет свободных мест. Пожалуйста, выберите другое время.",
                reply_markup=ReplyKeyboardMarkup(resize_keyboard=True)
                .add(KeyboardButton("Выбрать дату")))
            return
        
        paint(available_places, orange_places, fav_place)
        try:
            with open('img.jpg', 'rb') as photo:
                bot.send_photo(message.chat.id, photo)
        except FileNotFoundError:
            bot.send_message(message.chat.id, "Изображение не найдено")
        
        # Показываем доступные места
        show_available_places(message, available_places)
    
    elif 'place' not in user_data[user_id]:
        if message.text in get_available_places(user_data[user_id]['date'], user_data[user_id]['start_time'], user_data[user_id]['end_time'], message.from_user.id)[0]:
            user_data[user_id]['place'] = message.text
            
            # Подтверждение бронирования
            date_str = user_data[user_id]['date']
            start_time = user_data[user_id]['start_time']
            end_time = user_data[user_id]['end_time']
            place = user_data[user_id]['place']
            
            markup = ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(KeyboardButton("Подтвердить"), KeyboardButton("Отменить"))
            
            bot.send_message(
                message.chat.id,
                f"Подтвердите бронирование:\n\n"
                f"📅 Дата: *{date_str}*\n"
                f"⏰ Время: *{start_time} - {end_time}*\n"
                f"📍 Место: *{place}*",
                reply_markup=markup,
                parse_mode="Markdown"
            )

def show_available_places(message, available_places):
    """Показывает доступные места после выбора времени"""
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    
    buttons = [KeyboardButton(place) for place in available_places]
    for i in range(0, len(buttons), 3):
        row = buttons[i:i+3]
        markup.add(*row)
    
    markup.add(KeyboardButton("Назад"))
    
    bot.send_message(
        message.chat.id,
        "Выберите номер места:",
        reply_markup=markup
    )

if __name__ == "__main__":
    print("Бот запущен...")
    threading.Thread(target=check_upcoming_bookings, daemon=True).start()
    bot.infinity_polling(timeout=10, long_polling_timeout = 5)
