import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image
import struct

SIGN = b'RBIF'
SYNC = b'\xAA\x55'
BLOCK_PIXELS = 20

HEADER_STRUCT = struct.Struct('<HH')
BLOCK_HEAD = struct.Struct('<2sH')  # SYNC + block index


def crc_block(index, data):
    s = index & 0xFF
    for b in data:
        s ^= b
    return s & 0xFF


def encode_image():
    path = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.bmp")])
    if not path:
        return

    img = Image.open(path).convert("RGB")
    w, h = img.size
    pixels = list(img.getdata())

    save_path = filedialog.asksaveasfilename(defaultextension=".rbif",
                                             filetypes=[("Robust Image", "*.rbif")])
    if not save_path:
        return

    with open(save_path, "wb") as f:
        f.write(SIGN)
        f.write(HEADER_STRUCT.pack(w, h))

        total_pixels = len(pixels)
        block_index = 0

        for i in range(0, total_pixels, BLOCK_PIXELS):
            block = pixels[i:i+BLOCK_PIXELS]

            raw = bytearray()
            for r, g, b in block:
                raw.extend([r, g, b])

            # если последний блок меньше 20 — дополняем нулями
            while len(raw) < BLOCK_PIXELS * 3:
                raw.append(0)

            crc = crc_block(block_index, raw)

            f.write(BLOCK_HEAD.pack(SYNC, block_index))
            f.write(raw)
            f.write(struct.pack('B', crc))

            block_index += 1

    messagebox.showinfo("Готово", "Изображение закодировано.")


def decode_image():
    path = filedialog.askopenfilename(filetypes=[("Robust Image", "*.rbif;*.*")])
    if not path:
        return

    with open(path, "rb") as f:
        data = f.read()

    if len(data) < 8:
        messagebox.showerror("Ошибка", "Файл слишком мал.")
        return

    w, h = HEADER_STRUCT.unpack(data[4:8])
    total_pixels = w * h
    image_data = [(0, 0, 0)] * total_pixels

    i = 8
    size = len(data)

    while i < size - (2 + 2 + BLOCK_PIXELS*3 + 1):
        if data[i:i+2] == SYNC:
            try:
                _, block_index = BLOCK_HEAD.unpack_from(data, i)
                raw_start = i + 4
                raw_end = raw_start + BLOCK_PIXELS*3
                raw = data[raw_start:raw_end]
                crc = data[raw_end]

                if crc_block(block_index, raw) == crc:
                    pixel_start = block_index * BLOCK_PIXELS
                    for p in range(BLOCK_PIXELS):
                        idx = pixel_start + p
                        if idx >= total_pixels:
                            break
                        r = raw[p*3]
                        g = raw[p*3+1]
                        b = raw[p*3+2]
                        image_data[idx] = (r, g, b)

                i = raw_end + 1
                continue
            except:
                pass
        i += 1

    img = Image.new("RGB", (w, h))
    img.putdata(image_data)

    save_path = filedialog.asksaveasfilename(defaultextension=".png",
                                             filetypes=[("PNG Image", "*.png")])
    if save_path:
        img.save(save_path)
        messagebox.showinfo("Готово", "Восстановление завершено.")


root = tk.Tk()
root.title("Block-Resilient Image Format")

tk.Button(root, text="Кодировать", width=20, command=encode_image).pack(pady=10)
tk.Button(root, text="Декодировать", width=20, command=decode_image).pack(pady=10)

root.mainloop()