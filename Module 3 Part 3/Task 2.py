a = 0
for i in range(100, 1000):
    num = str(i)
    if num[0] == num[1] or num[0] == num[2] or num[1] == num[2]:
        a += 1
print(a)