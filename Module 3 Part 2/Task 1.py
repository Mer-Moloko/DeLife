sum_1 = 0
sum_2 = 0
sum_3 = 0

for i in range(int(input("Введите первое число: ")), int(input("Введите второе число: "))):
    if i % 2 == 0:
        sum_1 = sum_1 + 1
    else:
        sum_2 = sum_2 + 1
    if i % 9 == 0:
        sum_3 = sum_3 + 1

print(f"Четных чисел: {sum_1}")
print(f"Нечетных чисел: {sum_2}")
print(f"Чисел кратных 9: {sum_3}")