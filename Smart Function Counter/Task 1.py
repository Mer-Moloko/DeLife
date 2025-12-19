list = {"Count":0,
        "Name":"",
        "Argument":""}

def call_counter(func):
    def wrapper(a, b):
        func(a, b)
        list["Count"] += 1
        list["Name"] = func.__name__
        list["Argument"] = [a, b]
    return wrapper

@call_counter
def addition(a, b):
    print(a + b)

@call_counter
def subtraction(a, b):
    print(a + b)

@call_counter
def multiplication(a, b):
    print(a * b)

@call_counter
def division(a, b):
    print(a / b)

print("Кулькулятор с Личным ФСБ\n")

while True:
    print("Для выхода (X)\n"+
          "Для открытия журнала (Y)\n")
    example = input("Введите пример (a + b):").split()
    if example[0].lower() == "x":
        break
    elif example[0].lower() == "y":
        print(f"\nНомер вызова: {list["Count"]}\nНазвание последней функции: {list["Name"]}\nАргументы: {list['Argument']}")
    else:
        num_one = int(example[0])
        num_two = int(example[2])

        if example[1] == "+":
            addition(num_one, num_two)

        elif example[1] == "-":
            subtraction(num_one, num_two)

        elif example[1] == "*":
            multiplication(num_one, num_two)

        elif example[1] == "/":
            division(num_one, num_two)


