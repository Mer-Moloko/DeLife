a = int(input("Введите число начала диапазона: "))
b = int(input("Введите число конца диапазона: "))
for i in range(a, b):
    print(i)
for i in range(b, a, -1):
    print(i)
for i in range(a, b):
    if i % 7 == 0:
        print("Число кратное 7: ",i)
j = 0
for i in range(a, b):
    if i % 5 == 0:
        j = j + 1
print(f"Чисел кратным 5: {j}")