for num in range(int(input("Введите число начала диапазона: ")), int(input("Введите число конца диапазона: "))):
    if (num % 3 == 0) and (num % 5 == 0):
        print("Fizz Buzz")
    elif num % 3 == 0:
        print("Fizz")
    elif num % 5 == 0:
        print("Buzz")
    else:
        print(num)