list = input().split()
minus = 0
plus = 0
nulla = 0

print(f"Максимальное число: {max(list)}")
print(f"Минимальное число: {min(list)}")

for a in list:
    if int(a) < 0:
        minus += 1
print(f"Кол-во отрицательных элементов: {minus}")

for a in list:
    if int(a) > 0:
        plus += 1
print(f"Кол-во положительных элементов: {plus}")

for a in list:
    if int(a) == 0:
        nulla += 1
print(f"Кол-во нулевых элементов: {nulla}")