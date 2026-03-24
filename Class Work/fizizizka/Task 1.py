time = [2.1, 2.0, 2.2, 2.1, 2.1, 2.3, 2.0, 2.2, 2.1, 2.1]
print("\nЗадача: Измерение и погрешности (Маятник)")
print("-"*70)
print(f"Значения: {time}")
print("-"*70,"\nРезультаты:")
print(f"\tСреднее: {sum(time) / len(time)}")
print(f"\tАбсолютная погрешность: {(max(time) - min(time)) / 2}")
print(f"\tОтносительная погрешность: {(((max(time) - min(time)) / 2) / (sum(time) / len(time))) * 100}")
print("-"*70)
