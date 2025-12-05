import time


def print_char_by_char(text, delay=0.05):
    """
    Выводит текст посимвольно с задержкой

    Args:
        text: строка для вывода
        delay: задержка между символами в секундах (по умолчанию 0.05)
    """
    for char in text:
        print(char, end='', flush=True)  # flush=True сразу выводит символ
        time.sleep(delay)
    print()  # перевод строки в конце


# Пример использования
text = "Привет, мир! Этот текст выводится посимвольно."
print_char_by_char(text)

# С другой скоростью
print_char_by_char("Быстрее!", delay=0.02)