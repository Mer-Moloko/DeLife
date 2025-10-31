a = input("Введите букву для создание фигуры (а - к): ")
b = int(input("Введите размер: "))
if a == "a".lower():
    for i in range(1, b):
        print(" "*i+"*"*(b-i))
if a == "б".lower():
    for i in range(1, b):
        print("*" * i + " " * (b - i))
if a == "в".lower():
    for i in range(1, b):
        print(" " * i + "*" * (b - i) + "*" * (b - i))
if a == "г".lower():
    for i in range(1, b):
        print(" " * (b - i) + "*" * i + "*" * i)
if a == "д".lower():
    for i in range(1, b):
        print(" " * i + "*" * (b - i) + "*" * (b - i))
    for i in range(1, b):
        print(" " * (b - i) + "*" * i + "*" * i)
if a == "е".lower():
    for i in range(1, b):
        print("*" * i + " " * (b - i) + " " * (b - i) + "*" * i)
    for i in range(1, b):
        print("*" * (b - i) + " " * i + " " * i + "*" * (b - i))
if a == "ж".lower():
    for i in range(1, b):
        print("*" * i)
    for i in range(1, b):
        print("*" * (b - i))
if a == "з".lower():
    for i in range(1, b):
        print(" " * (b - i) + "*" * i )
    for i in range(1, b):
        print(" " * i + "*" * (b - i))
if a == "и".lower():
    for i in range(1, b):
        print("*" * (b - i))
if a == "к".lower():
    for i in range(1, b):
        print(" " * (b - i)+ "*" * i)

