in_call = [1, 2, 3]
out_call = [4, 5, 6]
operator = ["МТС", "Теле2", "Мегафон"]
print("Список операторов:\nМТС (1)\nТеле2 (2) \nМегафон (3)")

operator_one = int(input("Оператор первый (Введите номер оператора): "))
operator_two = int(input("Оператор второй (Введите номер оператора): "))

print(f"Звонок с {operator[operator_one-1]} на {operator[operator_two-1]} обойдется в {in_call[operator_one-1]+out_call[operator_two-1]} рублей в минуту")