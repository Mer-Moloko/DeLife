try:
    with open("text.txt") as f:
        text = f.read()

    null_str = 0
    for a in text.splitlines():
        if a == "":
            null_str += 1

    print(f"В файле строк - {len(text.splitlines())}, слов - {len(text.split())}, символов - {len(text)}, пустых строк - {null_str} ")

except FileNotFoundError:
    print("Файл не найден")

