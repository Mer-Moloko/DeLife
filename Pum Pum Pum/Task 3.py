import re

text = input("Введите текст: ")
a = re.split('[.!?]', text)
b = text.split()
k = 0
for i in text:
    if i == "!" or i == "?" or i == ".":
        k = k + 1

print(f"В тексте {len(a)-1} предложений, {len(b)} слов, {k} знаков ")