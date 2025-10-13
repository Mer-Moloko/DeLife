num = int(input("Введите число: "))
choice = int(input("Введите степень от 0 до 7: "))
if (choice > 0) and (choice <= 7):
    print(num**choice)
else:
    print("Введено число вне диапазона")