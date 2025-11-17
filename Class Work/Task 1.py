
import random

spells = ["Выстрел фаерболом", "Выстрел кофеем", "Создание круассана", "Спавн гиганто селедки", "Рой узбеков", "Распад Чехословакии"]
spellsPlayer = []

print("Добро пожаловать в школу великого магического Кудасая для магических гномов!!!")
while True:
    print("Что вы хотите сделать?\n"
          "Изучить новое заклинание (1)\n"
          "Показать список возможных заклинаний (2)\n"
          "Потренировать заклинание (3)\n"
          "Применить заклинание (4)\n"
          "Потеряться (Выход) (X)\n")
    choiceMenu = input()

    if choiceMenu == "1":
        while True:
            print("ИЗУЧЕНИЕ ЗАКЛИНАНИЯ")
            print("Для выхода (x)")
            print(f"Изученные заклинания: {spellsPlayer}")
            choiceSpell = input(f"Введите название заклинания из доступного списка {spells}: ")
            if choiceSpell in spellsPlayer:
                print(f"заклинание {choiceSpell} вы изучали!!!!!!!!")
            else:
                if choiceSpell in spells:
                    print("Попытка изучения")
                    if random.randint(1, 2) == 1:
                        spellsPlayer.append(choiceSpell)
                        print("Заклинание изучено")
                    else:
                        print("Заклинание вас рассыпало :3")
                elif choiceSpell == "x":
                    break
                else:
                    print("Заклинания нет в списке :3")

    if choiceMenu == "2":
        print("СПИСОК ЗАКЛИНАНИЙ")
        print(f"Список возможных заклинаний: {spells}")

    if choiceMenu == "3":
        print("ТРЕНИНГ")
        print("Для выхода (x)")
        while True:
            choiceSpell = input(f"Введите название заклинания из вашего списка {spellsPlayer}: ")
            if choiceSpell in spellsPlayer:
                print(f"Тренинг заклинания {choiceSpell} начался")
                if random.randint(1, 2) == 1:
                    print(f"Тренинг {choiceSpell} прошел успешно")
                else:
                    print("Гнома разнесло")
            else:
                print("Заклинание не изучено")

    if choiceMenu == "4":
        print("ПРИМЕНЕНИЕ ЗАКЛИНАНИЯ")
        print("Для выхода (x)")
        while True:
            choiceSpell = input(f"Введите название заклинания из вашего списка {spellsPlayer}: ")
            if choiceSpell in spellsPlayer:
                print(f"Заклинание {choiceSpell} произведено успешно")
            else:
                print("Заклинания нема")

    elif choiceMenu.lower() == "x":
        break



