print("Добро пожаловать в магазин любимого дефицита ссср!!!\n")
products = {
    "Сталин": frozenset({"очень редкое", "мощное"}),
    "Развал Чехословакии": frozenset({"редкое", "мощное"}),
    "Развал Югославии": frozenset({"редкое", "забытое"}),
    "Развал СССР": frozenset({"редкое", "разрывное"}),
    "Колбаска": frozenset({"редкое", "дефицитное"}),
    "Водочка": frozenset({"популярное", "для жигулей"}),
    "Личный КГБшник": frozenset({"популярное", "для семьи"}),
    "Конденсатор БМТ": frozenset({"популярное", "разрывное"}),
    "Орбита 107": frozenset({"кривое", "бесполезное"}),
    "Электроника ТА-003": frozenset({"кривое", "редкое"}),
    "Маринованный Ленин в собственном соку": frozenset({"для семьи", "редкое"})
}

def find_by_category(list, category):
    for product in list:

        print(list[product][0])

find_by_category(products, "ss")
while True:
    print("Меню:\n"
          "\tдобавить товар - 1\n"
          "\tвывести все товары - 2\n"
          "\tнайти товары по категории - 3\n"
          "\tвыйти - 4\n")
    choice = input("Введите число: ")

    if choice == "1":
        print("Добавим новый хлам!")

    elif choice == "2":
        print("Все товары: ")
        for name in products:
            print(f"\t{name}")

    elif choice == "3":
        print(
            f"Запущена Государственная Система Поиска Товаров Для Гражданского Использование На Территории Союза (ГСПТДГИНТС)\nДоступные категории: ")
        lists = []
        for name in products:
            for category in products[name]:
                lists.append(category)
        for names in set(lists):
            print(f"\t{names}")
        print("Введите название категории для поиска: ")
        name_category = input()

    elif choice == "4":
        break
    else:
        print("ТОВАРИЩ ВЫ ВВЕЛИ НЕ ПРАВИЛЬНОЕ ЗНАЧЕНИЕ!!!!")