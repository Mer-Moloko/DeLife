from datetime import date
week = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресение"]
day = date.weekday(date.today())
print("Сегодняшний день недели", week[day])

