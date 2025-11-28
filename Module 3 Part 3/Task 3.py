a = 0
for num in range(100, 10000):
    digits = str(num)
    if len(digits) == len(set(digits)):
        a += 1

print(a)