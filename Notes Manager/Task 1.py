print("Добро пожаловать в менеджер заметок")
notes = []
def load_notes():
    with open("Notes.txt", "r", encoding="utf-8") as f:
        data = f.readlines()
    for line in data:
        category, text = line.strip().split("|", 1)
        notes.append((category, text))
    return notes

def add_note(add_category, add_text):
    with open('Notes.txt', 'a', encoding='utf-8') as f:
        f.write(f"\n{add_category} | {add_text}")


while True:
    notes = []
    load_notes()
    print("\nМеню\n"
          "\t1 Добавить заметку\n"
          "\t2 Показать все заметки\n"
          "\t3 Найти заметки по категории\n"
          "\t4 Поиск по слову\n"
          "\t5 Выход")
    choice = input("Введите цифру: ")
    if choice == "1":
        print("Добавляем заметку:")
        add_note(input("\tВведите категорию: "), input("\tВведите текст: "))

    elif choice == "2":
        print("Все заметки:")
        for note in notes:
            print(f"\t{note[0]}|{note[1]}")

    elif choice == "3":
        print("Поиск заметки по категории")
        a = input("Введите категорию: ")
        for note in notes:
            if note[0].strip() == a:
                print(f"\t{note[0]}|{note[1]}")
        print("Поиск окончен")


    elif choice == "4":
        print("Поиск заметки по слову")
        a = input("Введите слово: ")

        for note in notes:
            for word in note[1].strip().split():
                if word == a:
                    print(f"\t{note[0]}|{note[1]}")
        print("Поиск окончен")

    elif choice == "5":
        break