text = input("Введите текст: ")
list = input("Введите список зарезервированных слов: ")
textOut = ""
for i in text.split():
    if i in list.split():
        textOut = textOut + i.upper() + " "
    else:
        textOut = textOut + i + " "
print(textOut)

    




