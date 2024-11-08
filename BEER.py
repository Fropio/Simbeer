import sqlite3

# 1. Подключение к базе данных
db = sqlite3.connect('beer.db')

# 2. Создание курсора для взаимодействия с базой данных
c = db.cursor()

# 3. Создание таблицы
# c.execute("""CREATE TABLE beer (
#   tip TEXT,
#   podtip TEXT,
#   name TEXT,
#   prozent INTEGER,
#   opisanie TEXT,
#   rub TEXT
# )""")

# 4. Удаление всех записей из таблицы (комментарий - пример удаления)
#c.execute("DELETE FROM beer")

# 5. Обновление записей в таблице (комментарий - пример обновления)
# c.execute("UPDATE deer SET")

# 6. Добавление новой записи в таблицу (комментарий - пример вставки)
#c.execute("INSERT INTO beer VALUES ('Светлое', 'Лагер', 'Джоус Светлый Лагер', 'Алкоголь: 4,9%', 'Jaws Lager - классика новой волны. Крафтовое пиво с многозначительной яркостью ячменного вкуса и мягкой цедровой горечью американских хмелей. Jaws Brewery— небольшая крафтовая пивоварня из города Заречный. ', '90 руб')" )

# 7. Выборка всех записей из таблицы (комментарий - пример выборки)
c.execute("SELECT * FROM beer")
# print(c.fetchone()) # Вывод первой записи
itu = c.fetchall()

for row in itu:
    print(row[0] + "\n" + row[1] + "\n" + row[2] + "\n" + str(row[3]) + "\n")

    # Разбиваем описание на строки по 40 символов
    opisanie = row[4]
    for i in range(0, len(opisanie), 40):
        # Добавляем абзац перед каждой новой строкой
        print(opisanie[i:i + 40])

    print( row[5] + "\n" )
# 8. Сохранение изменений в базе данных
db.commit()

# 9. Закрытие соединения с базой данных
db.close()
