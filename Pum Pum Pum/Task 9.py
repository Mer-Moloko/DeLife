product_list = {
    "Фрукты":
        [("Яблочки", 228, 50),
         ("Бананчики", 20219, 80),
         ("Cливчики", 80, 90)],
    "Овощи":
        [("Картоха", 23222323432, 999),
         ("Кабачок", 245, 100)],
    "Ягоды":
        [("Клубничка", 823, 200),
         ("Земляничка", 29, 3000)],
    "Молочка":
        [("МолОчко", 2323, 999),
         ("ПтИчЬе МоЛоЧкО", 22, 90000)],
    "Икра":
        [("Икра русалки", 1, 900000000),
         ("Дети моряка", 2, 5000),
         ("Красная", 5, 2000)],
    "Распад Чехословакии":
        [("Распад Чехословакии", 1, 12)]
}
sum_products = 0
max_sum_product = 0
max_category = 0
catcat = ""

print("добро пожаловать магазин разной ХеРнИ ^-^")
for products in product_list.keys():
    print(f"\nКатегория: {products}")
    for product in product_list[products]:
        print(f"\tНазвание: {product[0]}, Кол-во: {product[1]}, Цена - {product[2]}руб")
        if max_sum_product < product[2]:
            max_sum_product = product[2]
        sum_products += product[2]
    if len(product_list[products]) > max_category:
        max_category += 1
        catcat = products

print(f"\nСтоимость всех товаров: {sum_products} \nСамый дорогой товар: {max_sum_product} \nСамый большое кол-во товаров находится в категории: {catcat}")
