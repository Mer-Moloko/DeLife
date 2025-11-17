choice = input("Введите строку: ")
text = ""
for i in choice:
    if i != " ":
        text = text + i
if text == text[::-1]:
    print("Строка является палиндромом")
else:
    print("Строка не является палиндромом")