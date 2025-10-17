list_num = []
sum_num = 0
while True:
    a = int(input("Введите число: "))

    if a == 7:
        print("Good bye!")
        break
    list_num.append(a)
    sum_num = sum_num + a
print(f"Минимальное число: {min(list_num)}\nМаксимальное число: {max(list_num)}\nСумма чисел: {sum_num}")