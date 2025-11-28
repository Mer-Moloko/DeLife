text = input("Введите текст: ")
words = input("Введите запрещенные слова: ").split()
out = ""
for i in text.split():
    if i in words:
        out = out + " *** "
    else:
        out = out + i + " "

print(out)
