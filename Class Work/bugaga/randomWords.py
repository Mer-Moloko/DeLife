import random
text = "дверь кассета помидор жепа лес и светофор"
words = text.split()
random.shuffle(words)
print(' '.join(words))