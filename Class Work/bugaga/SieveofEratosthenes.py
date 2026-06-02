numbers = (1,5,6,2,4,6,7,8,79,5,4,35,3422,22,3,23,12)
def sas(n):
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True
print(sorted([num for num in numbers if sas(num)]))