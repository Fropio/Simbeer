import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import pymysql
import requests
import time

# Настройки
TOKEN = 'vk1.a.9gh-11AkqZOuknWqXQ8fOJs3XI0f741RrsO18Wog4mKaOF1FeC56WYh7-D_l2mPXaQ7ITq3YJQiWwas5R3oUW_3v4XCIsG5VJqEVIhtce0Y-TMxMG5HRU5dV7vdRaB_pcpDdxuY5epZKj3xX_AyFvHz3JvL81EUZjVYmej2Di7aW3RNB-ZxPLH7zR6VwwQT4RXdTaX20kjVQbKtSgANSEg'
ADMIN_IDS = [570718317, 291170303]  # ID администраторов

# Настройки базы данных MySQL
DB_HOST = '79.137.195.165'
DB_USER = 'gs2391'
DB_PASSWORD = '123456Alko!'
DB_NAME = 'gs2391'

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


def send_message(user_id, message, buttons=None, attachment=None):
    if buttons:
        keyboard = VkKeyboard(one_time=False)
        for row in buttons:
            for index, button in enumerate(row):
                if index % 4 == 0 and index != 0:
                    keyboard.add_line()
                keyboard.add_button(button['action']['label'],
                                    color=VkKeyboardColor.PRIMARY)
        keyboard = keyboard.get_keyboard()
    else:
        keyboard = VkKeyboard.get_empty_keyboard()

    vk.messages.send(
        user_id=user_id,
        message=message,
        random_id=0,
        keyboard=keyboard,
        attachment=attachment  # Используем правильно сформированный photo_id
    )


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


# Пример использования в функции добавления пива
def add_beer_stage(user_id, message, attachments=None):
    state = admin_states.get(user_id)

    if state is None:
        args = message.replace("/addbeer ", "").split('|')
        if len(args) < 9:
            send_message(
                user_id, "⚠️ Неверный формат. Используйте:\n"
                "/addbeer 🍺 Название | 🏷 Категория | 🔖 Подкатегория | 📏 Объем (л) | 🍃 Алкоголь (%) | 🌍 Страна | 💰 Цена (руб.) | ✏️ Описание | 🖼 URL Фото"
            )
            return

        name, category, subcategory, volume, alcohol, country, price, description, photo_url = args
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

        send_message(user_id, "🍺 Пиво успешно добавлено с фото! 🖼")

        # Сохраняем пиво в базу данных
        try:
            photo_id = upload_photo(
                photo_url)  # Загружаем фото и получаем photo_id
            with db.cursor() as cursor:
                sql = """INSERT INTO beers (name, category, type, volume, alcohol, country, price, description, photo_url)
                         VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
                cursor.execute(sql,
                               (name, category, subcategory, volume,
                                float(alcohol), country, float(price),
                                description, photo_id))  # Используем photo_id
                db.commit()

            send_message(
                user_id,
                f"🎉 Пиво '{name}' успешно Добавлено в базу!\n\n"
                f"🍺 Название: {name}\n"
                f"🏷 Категория: {category}\n"
                f"🔖 Подкатегория: {subcategory}\n"
                f"📏 Объем: {volume} л\n"
                f"🍃 Алкоголь: {alcohol}%\n"
                f"🌍 Страна: {country}\n"
                f"💰 Цена: {price} руб.\n"
                f"✏️ Описание: {description}\n"
                f"🖼 Фото: {photo_id}\n",  # Используем photo_id для отображения
                attachment=photo_id)
        except Exception as e:
            send_message(user_id, f"❌ Ошибка при добавлении пива: {e}")


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
        # Сообщение об ошибке
        send_message(
            user_id, f"❌ Ошибка при удалении пива с ID {beer_id}: {e}\n"
            "Пожалуйста, попробуйте снова.")


# Функция для просмотра всех доступных пив
def view_all_beers(user_id):
    with db.cursor() as cursor:
        cursor.execute(
            "SELECT id, name, category, type, price, photo_url FROM beers")
        beers = cursor.fetchall()

    if beers:
        message = "🍻 Список всех доступных пив:\n\n"
        for beer in beers:
            beer_id, name, category, beer_type, price, photo_url = beer
            message += (
                f"🆔 ID: {beer_id}\n"
                f"🍺 Название: {name}\n"
                f"🏷 Категория: {category}\n"
                f"🔖 Подкатегория: {beer_type}\n"
                f"💰 Цена: {price} руб.\n"
                f"🖼 Фото: {photo_url}\n\n"  # Добавляем ссылку на фото
            )
        send_message(user_id, message)
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
                     f"📝 Описание: {description}\n"
                     f"🖼 Фото: {photo_url}\n"
                     )  # Добавляем ссылку на фото в конец сообщения
        send_message(user_id, beer_info)
    else:
        send_message(user_id, "❌ Пиво с таким ID не найдено.")


# Функция для просмотра всех команд для администратора
def admin_help(user_id):
    help_text = (
        "👨‍💼 Список команд для администратора:\n\n"
        "➕ /addbeer Название|Категория|Подкатегория|Объем|Алкоголь|Страна|Цена|Описание|URL_фото — добавить новое пиво\n"
        "🗑 /deletebeer ID — удалить пиво по ID\n"
        "📋 /viewall — посмотреть список всех пив\n"
        "🔍 /checkbeer ID — посмотреть информацию о пиве по ID\n"
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


# Функции для отправки кндпок выбора
def send_country_buttons(user_id):
    # Функция для отправки кнопок выбора страны
    send_message(user_id, "Выберите страну:", buttons=["Россия", "Импортное"])


def send_category_buttons(user_id):
    # Функция для отправки кнопок каѴегорий
    send_message(user_id,
                 "Выберите категорию:",
                 buttons=["Светлое", "Тёмное", "Янтарное", "Золотистое"])


def send_subcategory_buttons(user_id):
    # Функция для отправки кнопок подкатегорий
    send_message(user_id,
                 "Выберите подкатегорию:",
                 buttons=["Лагерь", "Эль", "Пшеничное", "Портер"])


# Основной цикл бота
for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW and event.to_me:
        user_id = event.user_id
        message = event.text.strip(
        )  # Приводим текст к нижнему регистру для удобства

        # Приветственное сообщение и выбор страны
        if message == "начать" or message == "главное меню" or message == "Главное меню" or message == "Начать" or message == "старт" or message == "Старт" or message == "привет" or message == "Привет":
            send_message(
                user_id,
                "🍻 Добро пожаловать в наш мир пивных вкусов! 🌍\n\nИз какой страны вы бы хотели попробовать пиво? 🇩🇪🇧🇪🇺🇸\nВыберите страну, и мы подберем для вас лучшие сорта! 🍺",
                buttons=[[{
                    "action": {
                        "label": "Россия"
                    }
                }, {
                    "action": {
                        "label": "Импортное"
                    }
                }]])
            user_states[user_id] = {"stage": "awaiting_country"}
            continue

        # Команды администратора
        if user_id in ADMIN_IDS:
            if message.startswith("/addbeer"):
                add_beer_stage(user_id, message)
            elif event.attachments:  # Обрабатываем вложение, если оно есть
                add_beer_stage(user_id, "", event.attachments)
                continue
            elif message.startswith("/deletebeer"):
                try:
                    beer_id = int(message.split()[1])
                    delete_beer_by_id(user_id, beer_id)
                except (IndexError, ValueError):
                    send_message(user_id,
                                 "Укажите корректный ID для удаления.")
                continue
            elif message == "/viewall":
                view_all_beers(user_id)
                continue
            elif message.startswith("/checkbeer"):
                try:
                    beer_id = int(message.split()[1])
                    check_beer_by_id(user_id, beer_id)
                except (IndexError, ValueError):
                    send_message(user_id,
                                 "Укажите корректный ID для просмотра.")
                continue
            elif message == "/help":
                admin_help(user_id)
                continue
            elif message == "/admins":
                admins_list(user_id)
                continue

        # Обработка выбора страны пользователем
        elif user_id in user_states and user_states[user_id].get(
                "stage") == "awaiting_country":
            country = message.capitalize()
            if country in ["Россия", "Импортное"]:
                user_states[user_id] = {
                    "country": country,
                    "stage": "awaiting_category"
                }
                send_message(user_id, f"🎉 Вы выбрали страну: {country} 🌍\n\n")

                # Отправляем кнопки категорий
                send_message(user_id,
                             "Теперь выберите категорию пива 🍺:\n",
                             buttons=[[{
                                 "action": {
                                     "label": "Светлое"
                                 }
                             }, {
                                 "action": {
                                     "label": "Тёмное"
                                 }
                             }],
                                      [{
                                          "action": {
                                              "label": "Янтарное"
                                          }
                                      }, {
                                          "action": {
                                              "label": "Золотистое"
                                          }
                                      }]])
            else:
                send_message(
                    user_id,
                    "Пожалуйста, выберите одну из доступных стран: Россия или Импортное."
                )
            continue

        # Обработка выбора категории
        elif user_id in user_states and user_states[user_id].get(
                "stage") == "awaiting_category":
            category = message.capitalize()
            if category in ["Светлое", "Тёмное", "Янтарное", "Золотистое"]:
                user_states[user_id]["category"] = category
                user_states[user_id]["stage"] = "awaiting_subcategory"
                send_message(user_id,
                             f"🎉 Вы выбрали категорию: {category} 🍺\n\n")

                # Получаем подкатегории для выбранной категории и страны
                with db.cursor() as cursor:
                    cursor.execute(
                        "SELECT DISTINCT type FROM beers WHERE category = %s AND country = %s",
                        (category, user_states[user_id]["country"]))
                    subcategories = cursor.fetchall()

                # Проверяем наличие подкатегорий и отправляем кнопки
                if subcategories:
                    buttons = [[{
                        "action": {
                            "label": sub[0]
                        }
                    }] for sub in subcategories]
                    send_message(user_id,
                                 "Теперь выберите подкатегорию пива 🍻:\n",
                                 buttons)
                else:
                    send_message(
                        user_id,
                        "⚠️ Подкатегории для данной категории отсутствуют или данные не найдены 😕.\nПожалуйста, попробуйте выбрать другую категорию 🍻."
                    )
                    user_states[user_id][
                        "stage"] = "awaiting_category"  # Возврат на выбор категории
            else:
                send_message(
                    user_id,
                    "Пожалуйста, выберите одну из доступных категорий: Светлое, Тёмное, Янтарное, Золотистое."
                )
            continue

        # Обработка выбора подкатегории
        elif user_id in user_states and user_states[user_id].get(
                "stage") == "awaiting_subcategory":
            subcategory = message.capitalize()
            category = user_states[user_id]["category"]
            country = user_states[user_id]["country"]

            # Проверяем, есть ли пиво в выбранной стране, категории и подкатегории
            with db.cursor() as cursor:
                cursor.execute(
                    "SELECT name, price, volume, description, photo_url FROM beers WHERE category = %s AND type = %s AND country = %s",
                    (category, subcategory, country))
                beers = cursor.fetchall()

            # Отправка информации о пиве или сообщение об отсутствии вариантов
            if beers:
                response = f"Пиво из страны '{country}' категории '{category}' подкатегории '{subcategory}':\n\n"
                for beer in beers:
                    name, price, volume, description, photo_url = beer

                    # Проверяем, есть ли photo_id и корректный ли он
                    if photo_url:
                        # Отправляем сообщение с прикреплённой фотографией, если photo_id указан
                        send_message(
                            user_id,
                            f"🍺 {name}\n📏 Объем: {volume} л\n💰 Цена: {price} руб.\n📝 Описание: {description}\n📸 Фото: {photo_url}",
                        )
                    else:
                        # Отправляем сообщение без фотографии, если photo_id отсутствует
                        send_message(
                            user_id,
                            f"🍺 {name}\n📏 Объем: {volume} л\n💰 Цена: {price} руб.\n📝 Описание: {description}"
                        )
            else:
                send_message(
                    user_id,
                    f"Пиво в категории '{category}' и подкатегории '{subcategory}' не найдено."
                )
            continue
