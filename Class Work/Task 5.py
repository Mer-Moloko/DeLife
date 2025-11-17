text = input("Введите текст: ")
glas = ["а", "о", "у", "и", "ы", "э"]
soglas = ['б', 'в', 'г', 'д', 'ж', 'з', 'й', 'к', 'л', 'м', 'н', 'п', 'р', 'с', 'т', 'ф', 'х', 'ц', 'ч', 'ш', 'щ']
num_soglas = 0
num_glas = 0
print(f"Кол-во слов: {len(text.strip('.,!?').split())}")
print(f"Кол-во символов: {len(text)}")
for i in text:
    if i in soglas:
        num_soglas += 1
for i in text:
    if i in glas:
        num_glas += 1
print(f"Кол-во гласных: {num_glas}")
print(f"Ков-во согласных: {num_soglas}")
print(f"Самое длинное слов: {max(text.strip('.,!?').split(), key=len)}")


