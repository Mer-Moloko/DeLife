a = int(input("Введите начало диапазона: "))
b = int(input("Введите конец диапазона: "))
l = 0
for i in range(a, b):
    for j in range(1, i+1):
        if i % j == 0:
            l = l + 1
        #print(f"число i {i}, число j {j}, чсило l {l}")
    if l == 2:
        print(i)
    l = 0