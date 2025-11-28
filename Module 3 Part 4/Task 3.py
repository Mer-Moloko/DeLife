g = int(input("Введите начало диапазона: "))
c = int(input("Введите конец диапазона: "))
for a in range(g, c+1):
    for b in range(0, 11):
        print(f'{a} * {b} = {a * b}')
    print("\n")