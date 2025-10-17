manager_1 = int(input("Введите уровень продаж первого менеджера: "))
manager_2 = int(input("Введите уровень продаж второго менеджера: "))
manager_3 = int(input("Введите уровень продаж третьего менеджера: "))

def salary(manager):
    if manager < 500:
        manager = 200 + ((manager * 3) / 100)
    elif 500 < manager < 1000:
        manager = 200 + ((manager * 5) / 100)
    elif manager > 1000:
        manager = 200 + ((manager * 8) / 100)
    return manager

salary(manager_1)
salary(manager_2)
salary(manager_3)

print(f"Зарплата первого менеджера: {salary(manager_1)}")
print(f"Зарплата второго менеджера: {salary(manager_2)}")
print(f"Зарплата третьего менеджера: {salary(manager_3)}")

print(f"Лучший менеджер заработал: {max(salary(manager_1), salary(manager_2), salary(manager_3))}, получает премию 200$")