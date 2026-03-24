
newlist = {"Телефон":{"плоский", "афон", "электроника", "для отупления"},
        "Микроволновка":{"забавный", "игры", "огненное шоу", "электроника"},
        "4 Энергоблок":{"забавный", "огненное шоу", "электроника"},
        "Тефтелька":{"вкусный"},
        "Станки универсальные токарно-винторезные модели Б16Д25":{"электроника", "забавный"},
        "Фонарный столб":{"электроника"}}

list = sorted(newlist, key=lambda x: len(x))

def find_by_category(category):
    for keys in list:
        for value in list[keys]:
            if value == category:
                print("\t"+keys)

while True:
    print("\nВы зашли в магазин редких товаров")
    print("Меню:\n"
          "\t1 найти товары по категории\n"
          "\t2 вывести все товары\n"
          "\t3 добавить товар\n"
          "\t4 выйти\n")
    choices = input("Введите цифру: ")
    if choices == "1":
        print("\nMAX поиск товаров!")
        find_by_category(input("\tВведите название категории: "))
    if choices == "2":
        print("Список всех товаров:\n\t")
        for keys in list:
            print("\t"+keys)
    if choices == "3":
        print("\nДобавление товаров в MAX поиск!")
        name = input("Введите название товара: ")
        value = input("Введите категорию: ")
        list[name] = {value}

        print(list)
    if choices == "4":
        break
