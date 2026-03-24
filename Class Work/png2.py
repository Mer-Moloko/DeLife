import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import re


def encode_image_lossy(image_path):
    """
    Перекодирует PNG в оттенки серого, уменьшает разрешение в 2 раза.
    Сохраняет ширину и высоту в начале файла, а затем строки пикселей в HEX.
    """
    img = Image.open(image_path).convert("RGB")
    img = img.resize((img.width // 2, img.height // 2))
    img = img.convert("L")
    width, height = img.size
    pixels = list(img.getdata())

    lines = [f"{width} {height}"]  # первая строка: размеры
    for y in range(height):
        row_pixels = pixels[y * width:(y + 1) * width]
        hex_row = "".join(f"{p:02X}" for p in row_pixels)
        lines.append(hex_row)

    return "\n".join(lines)


def save_encoded_file(hex_data, original_path):
    txt_path = original_path.rsplit(".", 1)[0] + "_resilient.txt"
    with open(txt_path, "w") as f:
        f.write(hex_data)
    messagebox.showinfo("Сохранено", f"Файл сохранён как {txt_path}")


def load_resilient(file_path):
    """
    Загружает HEX-файл и восстанавливает изображение.
    Каждая строка восстанавливается отдельно, поврежденные строки игнорируются.
    """
    with open(file_path, "r") as f:
        lines = f.readlines()

    if not lines:
        return None

    try:
        width, height = map(int, lines[0].split())
    except:
        messagebox.showerror("Ошибка", "Невозможно прочитать размеры изображения.")
        return None

    img = Image.new("L", (width, height))

    for y, line in enumerate(lines[1:height + 1]):
        try:
            # оставляем только валидные HEX-символы
            hex_bytes = re.findall(r"[0-9A-Fa-f]{2}", line)
            row_pixels = [int(h, 16) for h in hex_bytes]
            for x, val in enumerate(row_pixels[:width]):
                img.putpixel((x, y), val)
        except:
            # если строка повреждена, оставляем черную
            continue

    return img


# --- GUI ---
root = tk.Tk()
root.title("Resilient PNG Encoder")

canvas = tk.Canvas(root, width=600, height=400)
canvas.pack()


def open_and_encode():
    file_path = filedialog.askopenfilename(filetypes=[("PNG files", "*.png")])
    if not file_path:
        return
    hex_data = encode_image_lossy(file_path)
    save_encoded_file(hex_data, file_path)


def view_file():
    file_path = filedialog.askopenfilename(filetypes=[("TXT files", "*.txt")])
    if not file_path:
        return
    img = load_resilient(file_path)
    if img:
        img_tk = ImageTk.PhotoImage(img)
        canvas.image = img_tk
        canvas.create_image(0, 0, anchor="nw", image=img_tk)
    else:
        messagebox.showerror("Ошибка", "Не удалось восстановить изображение")


# Кнопки
frame = tk.Frame(root)
frame.pack(pady=10)

btn_save = tk.Button(frame, text="Сохранить с потерями", command=open_and_encode)
btn_save.pack(side="left", padx=5)

btn_view = tk.Button(frame, text="Просмотр файла", command=view_file)
btn_view.pack(side="left", padx=5)

root.mainloop()
