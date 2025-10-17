while True:
    a = int(input("Введите число: "))
    if a == 7:
        print("Good bye!")
        break
    if a > 0:
        print("Number is positive")
    elif a < 0:
        print("Number is negative")
    else:
        print("Number is equal to zero")
