num = int(input("Введите число в диапазоне 1 - 100: "))

if (num < 100) and (num > 1):

    if (num % 3 == 0) and (num % 5 == 0):
        print("Fizz Buzz")
    elif num % 3 == 0:
        print("Fizz")
    elif num % 5 == 0:
        print("Buzz")
    else:
        print(num)

else:
    print("Число не в диапазоне")
