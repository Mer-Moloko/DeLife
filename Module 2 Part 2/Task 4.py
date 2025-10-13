numOne = int(input("Введите первое число: "))
numTwo = int(input("Введите второе число: "))
if numOne == numTwo:
    print("Числа равны")
elif numOne > numTwo:
    print(numTwo,",", numOne)
else:
    print(numOne,",", numTwo)
