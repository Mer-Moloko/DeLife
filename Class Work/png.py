i = 0
pos = 0
while i < len(body):
    if i + 4 > len(body):
        break
    delta = bytes_to_int(body[i:i+2])
    i += 2
    length = body[i]; i += 1
    color = body[i]; i += 1
    typ = body[i]; i += 1

    pos += delta
    if pos >= len(pixels):
        break  # защита от выхода за границы

    if typ == TYPE_SINGLE:
        if pos < len(pixels):
            pixels[pos] = color
        pos += 1
    elif typ == TYPE_RLE or typ == TYPE_RANGE:
        for k in range(length):
            if pos + k < len(pixels):
                pixels[pos + k] = color
        pos += length
