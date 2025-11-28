a = int(input("Введите начало диапазона: "))
b = int(input("Введите конец диапазона: "))
c = 0
for i in range(a, b):

    for j in range(1, i+1):




        if i == j:
            c =+ 1
        else:
            c =- 1

    if c > 0:
        print(i)
    c = 0



