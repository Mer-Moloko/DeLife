import math

R = 20
T = 40
h_osi = 22

omega = 2 * math.pi / T
V = omega * R
a_cs = V**2 / R
S_half = V * (T/2)
displacement_half = 2 * R

h_max = h_osi + R
h_min = h_osi - R
h_side = h_osi

t1 = 0
h1 = h_osi + R * math.sin(omega * t1 - math.pi/2)

t2 = 10
h2 = h_osi + R * math.sin(omega * t2 - math.pi/2)

t3 = 20
h3 = h_osi + R * math.sin(omega * t3 - math.pi/2)

t4 = 30
h4 = h_osi + R * math.sin(omega * t4 - math.pi/2)

print("ЗАДАЧА 4.1: КОЛЕСО ОБОЗРЕНИЯ")
print()
print("УСЛОВИЕ:")
print(f"Радиус колеса R = {R} м")
print(f"Период вращения T = {T} с")
print(f"Высота оси над землёй h_оси = {h_osi} м")
print("Найти: угловую скорость, линейную скорость,")
print("центростремительное ускорение, путь и перемещение за 20 с,")
print("высоту кабинки в разные моменты времени")
print()

print("РЕШЕНИЕ:")
print()

print("1. Угловая скорость вращения колеса:")
print(f"   ω = 2π/T = 2·3.1416/{T}")
print(f"   ω = {omega:.4f} рад/с")
print()

print("2. Линейная скорость кабинки:")
print(f"   V = ω·R = {omega:.4f}·{R}")
print(f"   V = {V:.2f} м/с")
print()

print("3. Центростремительное ускорение:")
print(f"   a_цс = V²/R = {V:.2f}²/{R}")
print(f"   a_цс = {a_cs:.2f} м/с²")
print()

print("4. Путь и перемещение за 20 с (половина оборота):")
print(f"   Путь S = V·t = {V:.2f}·20 = {S_half:.2f} м")
print(f"   Перемещение |r| = 2R = 2·{R} = {displacement_half} м")
print()

print("5. Высота кабинки над землёй:")
print(f"   Формула: h(t) = h_оси + R·sin(ω·t - π/2)")
print()
print(f"   В момент t = 0 с (нижняя точка):")
print(f"   h(0) = {h_osi} + {R}·sin({omega:.4f}·0 - π/2)")
print(f"   h(0) = {h1:.2f} м")
print()
print(f"   В момент t = 10 с (средняя точка, движется вверх):")
print(f"   h(10) = {h_osi} + {R}·sin({omega:.4f}·10 - π/2)")
print(f"   h(10) = {h2:.2f} м")
print()
print(f"   В момент t = 20 с (верхняя точка):")
print(f"   h(20) = {h_osi} + {R}·sin({omega:.4f}·20 - π/2)")
print(f"   h(20) = {h3:.2f} м")
print()
print(f"   В момент t = 30 с (средняя точка, движется вниз):")
print(f"   h(30) = {h_osi} + {R}·sin({omega:.4f}·30 - π/2)")
print(f"   h(30) = {h4:.2f} м")
print()

print("Проверка для полного оборота (40 с):")
print(f"   Путь = 2πR = 2·3.1416·{R} = {2*math.pi*R:.2f} м")
print(f"   Перемещение = 0 м (кабинка вернулась в исходную точку)")
print()

print("ОТВЕТ:")
print(f"ω = {omega:.4f} рад/с")
print(f"V = {V:.2f} м/с")
print(f"a_цс = {a_cs:.2f} м/с²")
print(f"За 20 с: путь S = {S_half:.2f} м, перемещение = {displacement_half} м")
print(f"Высота кабинки: h(0) = {h1:.2f} м, h(10) = {h2:.2f} м, h(20) = {h3:.2f} м, h(30) = {h4:.2f} м")
print()

print("+-----------------------------+-----------------------------+")
print("| Параметр                    | Значение                    |")
print("+-----------------------------+-----------------------------+")
print(f"| Радиус колеса R             | {R:>10.0f} м               |")
print(f"| Период T                    | {T:>10.0f} с               |")
print(f"| Угловая скорость ω          | {omega:>10.4f} рад/с       |")
print(f"| Линейная скорость V         | {V:>10.2f} м/с             |")
print(f"| Центростр. ускорение a_цс   | {a_cs:>10.2f} м/с²         |")
print(f"| Путь за 20 с                | {S_half:>10.2f} м          |")
print(f"| Перемещение за 20 с         | {displacement_half:>10.0f} м |")
print(f"| h(0)                        | {h1:>10.2f} м              |")
print(f"| h(10)                       | {h2:>10.2f} м              |")
print(f"| h(20)                       | {h3:>10.2f} м              |")
print(f"| h(30)                       | {h4:>10.2f} м              |")
print("+-----------------------------+-----------------------------+")
print()
print("=" * 70)
print()
print()
