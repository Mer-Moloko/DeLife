import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import numpy as np

def to_hex(value, length=2):
    return f"{value:0{length}X}"

def from_hex(s):
    return int(s, 16)

def load_image():
    global img, tk_img
    file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png;*.jpg;*.bmp")])
    if not file_path:
        return
    img = Image.open(file_path).convert("RGB")
    tk_img = ImageTk.PhotoImage(img)
    canvas.config(width=tk_img.width(), height=tk_img.height())
    canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)

def compress_image():
    if img is None:
        messagebox.showerror("Error", "Load an image first")
        return

    # уменьшение изображения 2×
    small = img.resize((img.width // 2, img.height // 2), Image.Resampling.LANCZOS)
    gray = small.convert("L")
    data = np.array(gray)
    h, w = data.shape

    max_square_size = 8  # максимальный размер квадрата
    min_square_size = 2  # минимальный размер квадрата
    threshold = 50       # порог похожести внутри квадрата

    save_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text file", "*.txt")])
    if not save_path:
        return

    squares = []

    # простой алгоритм: ищем квадраты сверху вниз, слева направо
    for y in range(0, h, min_square_size):
        for x in range(0, w, min_square_size):
            for size in range(max_square_size, min_square_size-1, -1):
                if x + size > w or y + size > h:
                    continue
                block = data[y:y+size, x:x+size]
                min_val, max_val = block.min(), block.max()
                if max_val - min_val <= threshold:
                    avg_color = int(block.mean())
                    squares.append((size, x, y, avg_color))
                    # закрашиваем уже выбранные пиксели чтобы не повторять
                    data = np.array(gray, dtype=np.int16)

                    break

    # запись в UTF-8
    with open(save_path, "w", encoding="utf-8") as f:
        for size, x, y, color in squares:
            f.write(f"{to_hex(size,2)},{to_hex(x,2)},{to_hex(y,2)},{to_hex(color,2)}\n")

    messagebox.showinfo("Saved", "Image compressed using squares!")

def decompress_image():
    file_path = filedialog.askopenfilename(filetypes=[("Text file", "*.txt")])
    if not file_path:
        return

    pixels = []
    max_x = 0
    max_y = 0

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                size_hex, x_hex, y_hex, color_hex = line.split(",")
                size = from_hex(size_hex)
                x = from_hex(x_hex)
                y = from_hex(y_hex)
                color = from_hex(color_hex)
                for j in range(size):
                    for i in range(size):
                        px = x + i
                        py = y + j
                        pixels.append((px, py, color))
                        max_x = max(max_x, px+1)
                        max_y = max(max_y, py+1)
            except:
                continue

    if not pixels:
        messagebox.showerror("Error", "No valid data found")
        return

    img_out = Image.new("L", (max_x, max_y))
    for x, y, color in pixels:
        img_out.putpixel((x, y), color)

    img_out.show()


# GUI
root = tk.Tk()
root.title("Square-Based Image Compressor")

img = None
tk_img = None

frame = tk.Frame(root)
frame.pack()

load_btn = tk.Button(frame, text="Load Image", command=load_image)
load_btn.pack(side=tk.LEFT, padx=5)

compress_btn = tk.Button(frame, text="Compress Image", command=compress_image)
compress_btn.pack(side=tk.LEFT, padx=5)

decompress_btn = tk.Button(frame, text="Decompress Image", command=decompress_image)
decompress_btn.pack(side=tk.LEFT, padx=5)

canvas = tk.Canvas(root)
canvas.pack()

root.mainloop()
