import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import pymysql
import requests
import time

# Настройки
TOKEN = 'vk1.a.9gh-11AkqZOuknWqXQ8fOJs3XI0f741RrsO18Wog4mKaOF1FeC56WYh7-D_l2mPXaQ7ITq3YJQiWwas5R3oUW_3v4XCIsG5VJqEVIhtce0Y-TMxMG5HRU5dV7vdRaB_pcpDdxuY5epZKj3xX_AyFvHz3JvL81EUZjVYmej2Di7aW3RNB-ZxPLH7zR6VwwQT4RXdTaX20kjVQbKtSgANSEg'
ADMIN_IDS = [
    570718317, 291170303, 242662322
]  # ID администраторов 291170303 - Тёма, 570718317 - Марк, 242662322 - Сергей

# Настройки базы данных MySQL
# DB_HOST = '79.137.195.165'
# DB_USER = 'gs2391'
# DB_PASSWORD = '123456Alko!'
# DB_NAME = 'gs2391'
DB_HOST = '51.91.215.125'
DB_USER = 'gs279651'
DB_PASSWORD = '123456Alko!'
DB_NAME = 'gs279651'

# Подключение к базе данных
db = pymysql.connect(host=DB_HOST,
                     user=DB_USER,
                     password=DB_PASSWORD,
                     database=DB_NAME,
                     charset='utf8mb4')

# Подключение к VK API
vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()
longpoll = VkLongPoll(vk_session)

# Состояния
admin_states = {}
user_states = {}
# Указываем список стран
COUNTRIES = ["Россия", "Импортное"]


def send_message(user_id,
     message,
     buttons=None,
     attachment=None,
     add_back=False):
    MAX_MESSAGE_LENGTH = 4096  # Максимально допустимая длина сообщения ВКонтакте

    if buttons:
        keyboard = VkKeyboard(one_time=False)
        for row in buttons:
            for index, button in enumerate(row):
                if index % 4 == 0 and index != 0:
                    keyboard.add_line()
                keyboard.add_button(button['action']['label'],
                                    color=VkKeyboardColor.PRIMARY)

        # Добавляем кнопку "Назад" только если add_back=True
        if add_back:
            keyboard.add_line()
            keyboard.add_button("Назад", color=VkKeyboardColor.NEGATIVE)
        keyboard = keyboard.get_keyboard()
    else:
        keyboard = VkKeyboard.get_empty_keyboard()

    # Отправка сообщения с проверкой на длину
    if len(message) <= MAX_MESSAGE_LENGTH:
        # Если сообщение не превышает лимит, отправляем его целиком
        vk.messages.send(user_id=user_id,
                 message=message,
                 random_id=0,
                 keyboard=keyboard,
                 attachment=attachment)
    else:
        # Если сообщение слишком длинное, разбиваем его на части и отправляем по очереди
        for i in range(0, len(message), MAX_MESSAGE_LENGTH):
            part = message[i:i + MAX_MESSAGE_LENGTH]
            vk.messages.send(user_id=user_id,
                 message=part,
                 random_id=0,
                 keyboard=keyboard,
                 attachment=attachment)



# Функция для загрузки фотографии на сервер VK и возвращения его ID
def upload_photo(photo_url):
    upload_url = vk.photos.getMessagesUploadServer()["upload_url"]
    photo_data = requests.get(photo_url).content
    response = requests.post(upload_url,
                             files={
                                 "photo":
                                 ("photo.jpg", photo_data, "image/jpeg")
                             }).json()
    saved_photo = vk.photos.saveMessagesPhoto(photo=response["photo"],
                                              server=response["server"],
                                              hash=response["hash"])[0]
    return f'photo{saved_photo["owner_id"]}_{saved_photo["id"]}'


def add_beer_stage(user_id, message, attachments=None):
    try:
        state = admin_states.get(user_id)

        if state is None:
            try:
                # Разбираем сообщение на параметры
                args = message.replace("/addbeer ", "").split('|')
                if len(args) < 9:
                    send_message(
                        user_id, "⚠️ Неверный формат. Используйте:\n"
                        "/addbeer 🍺 Название | 🏷 Категория | 🔖 Подкатегория | 📏 Объем (л) | 🍃 Алкоголь (%) | 🌍 Страна | 💰 Цена (руб.) | ✏️ Описание | 🖼 URL Фото"
                    )
                    admin_states[user_id] = None  # Сбрасываем состояние
                    return

                # Извлекаем параметры
                name, category, subcategory, volume, alcohol, country, price, description, photo_url = args

                # Сохраняем состояние администратора
                admin_states[user_id] = {
                    "name": name,
                    "category": category,
                    "subcategory": subcategory,
                    "volume": volume,
                    "alcohol": alcohol,
                    "country": country,
                    "price": price,
                    "description": description,
                    "photo_url": photo_url,
                    "stage": "awaiting_photo"
                }

                # Пытаемся загрузить фото
                try:
                    photo_id = upload_photo(
                        photo_url)  # Загружаем фото и получаем photo_id
                except Exception as upload_error:
                    send_message(user_id,
                                 f"❌ Ошибка загрузки фото: {upload_error}")
                    admin_states[user_id] = None  # Сбрасываем состояние
                    return

                # Пытаемся сохранить данные в базе данных
                try:
                    with db.cursor() as cursor:
                        sql = """INSERT INTO beers (name, category, type, volume, alcohol, country, price, description, photo_url)
                                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
                        cursor.execute(
                            sql,
                            (name, category, subcategory, volume,
                             float(alcohol), country, float(price),
                             description, photo_id))  # Используем photo_id
                        db.commit()

                    # Отправляем сообщение об успешном добавлении
                    send_message(
                        user_id,
                        f"🎉 Пиво '{name}' успешно добавлено в базу!\n\n"
                        f"🍺 Название: {name}\n"
                        f"🏷 Категория: {category}\n"
                        f"🔖 Подкатегория: {subcategory}\n"
                        f"📏 Объем: {volume} л\n"
                        f"🍃 Алкоголь: {alcohol}%\n"
                        f"🌍 Страна: {country}\n"
                        f"💰 Цена: {price} руб.\n"
                        f"✏️ Описание: {description}\n"
                        f"🖼 Фото:\n",  # Используем photo_id для отображения
                        attachment=photo_id)

                    # Сбрасываем состояние администратора для подготовки к следующему добавлению
                    admin_states[user_id] = None

                except Exception as db_error:
                    send_message(
                        user_id,
                        f"❌ Ошибка при добавлении в базу данных: {db_error}")
                    admin_states[user_id] = None  # Сбрасываем состояние
                    return

            except Exception as e:
                # Обработка любых других ошибок
                send_message(user_id,
                             f"❌ Общая ошибка при обработке команды: {e}")
                admin_states[user_id] = None  # Сбрасываем состояние

    except Exception as fatal_error:
        # Если что-то серьезно пошло не так, сообщаем об этом, но не прерываем работу бота
        send_message(user_id, f"⚠️ Критическая ошибка: {fatal_error}")
        admin_states[user_id] = None  # Сбрасываем состояние


# Функция для удаления пива по ID
def delete_beer_by_id(user_id, beer_id):
    try:
        with db.cursor() as cursor:
            # Выполняем удаление пива по ID
            cursor.execute("DELETE FROM beers WHERE id = %s", (beer_id, ))
            db.commit()

        # Сообщение об успешном удалении пива
        send_message(
            user_id, f"🗑️ Пиво с ID {beer_id} успешно удалено!\n"
            "🍻 Надеемся, вы добавите что-то новое скоро!")
    except Exception as e:
        send_message(user_id, f"❌ Ошибка при добавлении пива: {e}")
        admin_states.pop(user_id, None)  # Сброс состояния
        return

def view_all_beers(user_id):
    with db.cursor() as cursor:
        cursor.execute(
            "SELECT id, name, category, type, price, country FROM beers")
        beers = cursor.fetchall()

    if beers:
        # Создаем словарь для подсчета количества пива по категории и подкатегории, а также для сохранения их названий
        country_category_data = {}

        for beer in beers:
            beer_id, name, category, beer_type, price, country = beer

            # Структура данных: Страна -> Категория -> Подкатегория -> Пиво
            if country not in country_category_data:
                country_category_data[country] = {}
            if category not in country_category_data[country]:
                country_category_data[country][category] = {}
            if beer_type not in country_category_data[country][category]:
                country_category_data[country][category][beer_type] = []

            # Добавляем ID и название пива в соответствующую подкатегорию
            country_category_data[country][category][beer_type].append((beer_id, name))

        # Формируем и отправляем сообщения с итогом по странам, категориям и подкатегориям
        total_beers = 0
        final_message = "🍻 Итоговый список доступного пива:\n\n"

        for country, categories in country_category_data.items():
            # Разделитель перед каждой новой страной
            final_message += "-----------------------------------\n"
            final_message += f"🌍 Страна: {country}\n\n"
            for category, types in categories.items():
                final_message += f"  📘 Категория: {category}\n"
                for beer_type, beers in types.items():
                    beer_count = len(beers)
                    total_beers += beer_count
                    # Названия пива перечисляются после подкатегории
                    final_message += (f"    🔖 Подкатегория: {beer_type} "
                                      f"(всего {beer_count}):\n")
                    final_message += "".join(
                        [f"      ----- ID: {beer_id} | {name}\n" for beer_id, name in beers])

        final_message += f"\n🍺 Всего доступно сортов пива: {total_beers}"

        send_message(user_id, final_message)
    else:
        send_message(user_id, "❌ В данный момент нет доступных пив.")

# Функция для просмотра информации о пиве по ID с фото
def check_beer_by_id(user_id, beer_id):
    with db.cursor() as cursor:
        cursor.execute(
            "SELECT name, category, type, volume, alcohol, country, price, description, photo_url FROM beers WHERE id = %s",
            (beer_id, ))
        beer = cursor.fetchone()

    if beer:
        name, category, beer_type, volume, alcohol, country, price, description, photo_url = beer
        beer_info = (f"🍺 Название: {name}\n"
                     f"🏷 Категория: {category}\n"
                     f"🔖 Подкатегория: {beer_type}\n"
                     f"📦 Объем: {volume} л\n"
                     f"🍷 Алкоголь: {alcohol}%\n"
                     f"🌍 Страна: {country}\n"
                     f"💰 Цена: {price} руб.\n"
                     f"📝 Описание: {description}\n")

        # Проверяем, если photo_url и добавляем как attachment
        attachment = photo_url if photo_url else None
        send_message(user_id, beer_info, attachment=attachment)
    else:
        send_message(user_id, "❌ Пиво с таким ID не найдено.")


# Функция для просмотра всех команд для администратора
def admin_help(user_id):
    help_text = (
        "👨‍💼 Список команд для администратора:\n\n"
        "➕ /addbeer Название | Категория | Подкатегория | Объем | Алкоголь | Страна | Цена | Описание | URL_фото — добавить новое пиво\n"
        "🗑 /deletebeer ID — удалить пиво по ID\n"
        "📋 /viewall — посмотреть список всех пив\n"
        "🔍 /checkbeer ID — посмотреть информацию о пиве по ID\n"
        "📝 /searchbeer Название — найти пиво по названию\n"
        "❓ /help — посмотреть список команд\n")
    send_message(user_id, help_text)


def admins_list(user_id):
    admins = [{
        "name": "@id570718317 | Владислав Миронов",
        "position": "Разработчик 1"
    }, {
        "name": "@id291170303 | Артём Зимнухов",
        "position": "Разработчик 2"
    }, {
        "name": "@id242662322 | Сергей Симуков",
        "position": "Разработчик 3"
    }]

    message = "👑 Список администраторов:\n"

    for admin in admins:
        message += f"{admin['name']} - {admin['position']}\n"

    send_message(user_id, message)


def send_buttons(user_id, text, button_labels, add_back=False):
    """Функция отправляет текст с кнопками, включая кнопку 'Назад', если add_back=True."""
    buttons = [[{
        "action": {
            "label": label
        }
    } for label in row] for row in button_labels]
    send_message(user_id, text, buttons=buttons, add_back=add_back)


#ТЕСТИМ
def search_beer_by_name(user_id, search_term):
    """Ищет пиво по названию и отправляет результаты администратору."""
    with db.cursor() as cursor:
        cursor.execute(
            "SELECT id, name, category, type, price, country, photo_url FROM beers WHERE name LIKE %s",
            (f"%{search_term}%", ))
        beers = cursor.fetchall()

    if beers:
        for beer in beers:
            beer_id, name, category, beer_type, price, country, photo_url = beer
            message = (f"🆔 ID: {beer_id}\n"
                       f"🍺 Название: {name}\n"
                       f"🏷 Категория: {category}\n"
                       f"🔖 Подкатегория: {beer_type}\n"
                       f"🌍 Страна: {country}\n"
                       f"💰 Цена: {price} руб.\n")
            attachment = photo_url if photo_url else None
            send_message(user_id, message, attachment=attachment)
    else:
        send_message(user_id, "❌ Пиво с таким названием не найдено.")


# Функции для каждого этапа
def send_country_buttons(user_id):
    send_buttons(
        user_id,
        "🍻 Добро пожаловать в наш мир пивных вкусов! 🌍\n\nИз какой страны вы бы хотели попробовать пиво? 🇩🇪🇧🇪🇺🇸\nВыберите страну, и мы подберем для вас лучшие сорта! 🍺",
        [["Россия", "Импортное"]])


def send_category_buttons(user_id):
    send_buttons(user_id,
                 "Теперь выберите категорию пива 🍺:",
                 [["Светлое", "Тёмное"], ["Янтарное", "Золотистое"]],
                 add_back=True)


def send_subcategory_buttons(user_id, category):
    country = user_states[user_id]["country"]
    with db.cursor() as cursor:
        # Условие для импортного пива: страна != "Россия"
        if country == "Импортное":
            cursor.execute(
                "SELECT DISTINCT type FROM beers WHERE category = %s AND country != %s",
                (category, 'Россия'))
        else:
            # Для российского пива фильтруем по конкретной стране
            cursor.execute(
                "SELECT DISTINCT type FROM beers WHERE category = %s AND country = %s",
                (category, country))
        subcategories = cursor.fetchall()

    # Проверяем и отправляем пользователю список подкатегорий
    if subcategories:
        send_buttons(user_id,
                     "Теперь выберите подкатегорию пива 🍻:",
                     [[sub[0] for sub in subcategories]],
                     add_back=True)
    else:
        send_message(
            user_id,
            "Подкатегории отсутствуют. Попробуйте выбрать другую категорию.")
        user_states[user_id]["stage"] = "awaiting_category"


# Обработка нажатия кнопки "Назад"
def handle_back(user_id, user_stage):
    stages = {
        "awaiting_category": ("awaiting_country", send_country_buttons),
        "awaiting_subcategory": ("awaiting_category", send_category_buttons),
        "awaiting_beer": ("awaiting_subcategory", send_subcategory_buttons)
    }
    if user_stage in stages:
        new_stage, send_func = stages[user_stage]
        send_func(user_id)
        user_states[user_id]["stage"] = new_stage


def handle_admin_commands(user_id, message, attachments=None):
    """Обрабатывает команды администраторов."""
    if message.startswith("/addbeer"):
        add_beer_stage(user_id, message)
    elif attachments:
        add_beer_stage(user_id, "", attachments)
    elif message.startswith("/deletebeer"):
        try:
            beer_id = int(message.split()[1])
            delete_beer_by_id(user_id, beer_id)
        except (IndexError, ValueError):
            send_message(user_id, "Укажите корректный ID для удаления.")
    elif message == "/viewall":
        view_all_beers(user_id)
    elif message.startswith("/checkbeer"):
        try:
            beer_id = int(message.split()[1])
            check_beer_by_id(user_id, beer_id)
        except (IndexError, ValueError):
            send_message(user_id, "Укажите корректный ID для просмотра.")
    elif message == "/help":
        admin_help(user_id)
    elif message == "/admins":
        admins_list(user_id)
    elif message.startswith("/searchbeer"):
        # Ищем пиво по названию
        search_term = message.replace("/searchbeer ", "").strip()
        search_beer_by_name(user_id, search_term)


# Основной цикл бота
for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW and event.to_me:
        user_id = event.user_id
        message = event.text.strip(
        )  #.lower() добавить после добавления всего пивка

        # Кнопка "Назад"
        if message == "назад":
            user_stage = user_states.get(user_id, {}).get("stage")
            handle_back(user_id, user_stage)
            continue

        # Приветственные сообщения
        greetings = {
            "начать", "главное меню", "старт", "привет", "Привет", "Начать",
            "Старт", "Меню", "Главное меню", "меню"
        }
        if message in greetings:
            send_buttons(
                user_id,
                "🍻 Добро пожаловать в наш мир пивных вкусов! 🌍\n\nИз какой страны вы бы хотели попробовать пиво? 🇩🇪🇧🇪🇺🇸\nВыберите страну, и мы подберем для вас лучшие сорта! 🍺",
                [["Россия", "Импортное"]])
            user_states[user_id] = {"stage": "awaiting_country"}
            continue

        # Команды администратора
        if user_id in ADMIN_IDS:
            handle_admin_commands(user_id, message, event.attachments)
            continue
        # Этапы выбора страны, категории и подкатегории
        stage = user_states.get(user_id, {}).get("stage")

        # Этап: Выбор страны
        if stage == "awaiting_country":
            if message.capitalize() in ["Россия", "Импортное"]:
                user_states[user_id] = {
                    "country": message.capitalize(),
                    "stage": "awaiting_category"
                }
                send_buttons(
                    user_id,
                    f"🎉 Вы выбрали страну: {message.capitalize()} 🌍\n\nТеперь выберите категорию пива 🍺:",
                    [["Светлое", "Тёмное"], ["Янтарное", "Золотистое"]],
                    add_back=True)
            else:
                send_message(user_id,
                             "Пожалуйста, выберите: Россия или Импортное.")
            continue

        # Этап: Выбор категории
        elif stage == "awaiting_category":
            category = message.capitalize()
            if category in ["Светлое", "Тёмное", "Янтарное", "Золотистое"]:
                user_states[user_id]["category"] = category
                user_states[user_id]["stage"] = "awaiting_subcategory"

                # Отображаем выбранную категорию
                send_message(
                    user_id,
                    f"🎉 Вы выбрали категорию: {category} 🍺\n\nТеперь выберите подкатегорию пива 🍻:"
                )

                # Получаем подкатегории из БД для выбранной страны
                country = user_states[user_id]["country"]
                with db.cursor() as cursor:
                    # Проверяем, выбрано ли "Импортное" (все страны, кроме России)
                    if country == "Импортное":
                        cursor.execute(
                            "SELECT DISTINCT type FROM beers WHERE category = %s AND country != %s",
                            (category, 'Россия'))
                    else:
                        # Иначе отображаем подкатегории для конкретной страны
                        cursor.execute(
                            "SELECT DISTINCT type FROM beers WHERE category = %s AND country = %s",
                            (category, country))
                    subcategories = cursor.fetchall()

                # Проверяем и отправляем подкатегории пользователю
                if subcategories:
                    send_buttons(user_id,
                                 "Подкатегории:",
                                 [[sub[0] for sub in subcategories]],
                                 add_back=True)
                else:
                    send_message(
                        user_id,
                        "Подкатегории отсутствуют. Попробуйте выбрать другую категорию."
                    )
                    user_states[user_id]["stage"] = "awaiting_category"
            else:
                send_message(
                    user_id,
                    "Выберите: Светлое, Тёмное, Янтарное или Золотистое.")
            continue

        # Этап: Выбор подкатегории
        elif stage == "awaiting_subcategory":
            subcategory = message.capitalize()
            country = user_states[user_id]["country"]
            category = user_states[user_id]["category"]

            # Отправляем пиво для выбранной страны, категории и подкатегории
            with db.cursor() as cursor:
                # Если страна "Импортное", выбираем все страны, кроме России
                if country == "Импортное":
                    cursor.execute(
                        "SELECT name, price, volume, description, alcohol, photo_url FROM beers WHERE category = %s AND type = %s AND country != %s",
                        (category, subcategory, 'Россия'))
                else:
                    # Для российских товаров выбираем конкретную страну
                    cursor.execute(
                        "SELECT name, price, volume, description, alcohol, photo_url FROM beers WHERE category = %s AND type = %s AND country = %s",
                        (category, subcategory, country))
                beers = cursor.fetchall()

            if beers:
                for name, price, volume, description, alcohol, photo_url in beers:
                    text = (f"🍺 {name}\n"
                            f"📏 Объем: {volume} л\n"
                            f"💰 Цена: {price} руб.\n"
                            f"📝 Описание: {description}\n"
                            f"🥂 Алкоголь: {alcohol}%")
                    send_message(user_id,
                                 text,
                                 attachment=photo_url if photo_url else None)

                # Отправляем кнопку "Назад" после показа пива
                send_buttons(
                    user_id,
                    f"Вы выбрали подкатегорию: {subcategory} 🍻\nХотите вернуться к выбору категории?",
                    [["Назад"]])
            else:
                send_message(
                    user_id,
                    f"Пиво в '{category}' и '{subcategory}' не найдено.")

            continue
