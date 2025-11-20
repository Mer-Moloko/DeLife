text = input().split()
out = ""
if text[1] == "-":
    out = int(text[0]) - int(text[2])
elif text[1] == "+":
    out = int(text[0]) + int(text[2])
elif text[1] == "/":
    out = int(text[0]) / int(text[2])
elif text[1] == "*":
    out = int(text[0]) * int(text[2])
print(out)