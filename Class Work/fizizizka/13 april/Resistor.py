resistors = []
a = []
print("Программа расчета сопротивления резисторов")
while True:
    print("Меню\n"
          "\t1 Параллельное соединение\n"
          "\t2 Последовательное соединение\n"
          "\t3 Выход")
    choice = input()
    if choice == "1":
        print("\tПараллельное соединение")
        print("Если закончили 0, для выхода -1")
        while True:
            choice = input("Добавьте резистор (сопротивление в омах): ")
            if choice == "0":
                for i in resistors:
                    a.append(i / len(resistors))
                print(f"Итоговая сумма {sum(a) / len(a)}")
                resistors.clear()
                a.clear()

            if choice == "-1":
                break
            else:
                resistors.append(int(choice))


    if choice == "2":
        print("\tПоследовательное соединение")
        print("Если закончили 0, для выхода -1")
        while True:
            choice = input("Добавьте резистор (сопротивление в омах): ")
            if choice == "0":
                print(f"Итоговая сумма: {sum(resistors)}")
                resistors.clear()
            if choice == "-1":
                break
            else:
                resistors.append(int(choice))


    if choice == "3":
        break