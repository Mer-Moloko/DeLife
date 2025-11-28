import re

text = input("Введите текст: ")
a = re.split('[.!?]', text)

print(f"В тексте {len(a)-1} предложений")