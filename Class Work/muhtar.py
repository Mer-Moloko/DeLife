import tkinter as tk
from tkinter import filedialog, messagebox
import numpy as np
from scipy.io import wavfile
import struct

# ---------------- НАДЁЖНЫЕ ПАРАМЕТРЫ ----------------

SAMPLE_RATE = 96000
SYMBOL_DURATION = 0.03  # 40 мс
N_SUBCARRIERS = 192
FREQ_START = 500
FREQ_END = 18000

AMPLITUDE = 12000
THRESHOLD_RATIO = 0.35  # адаптивный порог

# ----------------------------------------------------

samples_per_symbol = int(SAMPLE_RATE * SYMBOL_DURATION)
freqs = np.linspace(FREQ_START, FREQ_END, N_SUBCARRIERS)


def encode_file():
    filepath = filedialog.askopenfilename()
    if not filepath:
        return

    with open(filepath, "rb") as f:
        data = f.read()

    header = struct.pack("I", len(data))
    data = header + data

    bitstream = "".join(format(byte, "08b") for byte in data)

    bits_per_symbol = N_SUBCARRIERS

    if len(bitstream) % bits_per_symbol != 0:
        padding = bits_per_symbol - (len(bitstream) % bits_per_symbol)
        bitstream += "0" * padding

    symbols = [
        bitstream[i:i+bits_per_symbol]
        for i in range(0, len(bitstream), bits_per_symbol)
    ]

    t = np.linspace(0, SYMBOL_DURATION, samples_per_symbol, endpoint=False)
    output = np.array([], dtype=np.float32)

    for symbol_bits in symbols:
        signal = np.zeros(samples_per_symbol)

        for i, bit in enumerate(symbol_bits):
            if bit == "1":
                signal += AMPLITUDE * np.sin(2 * np.pi * freqs[i] * t)

        output = np.concatenate((output, signal))

    output = np.int16(output / np.max(np.abs(output)) * 32767)

    save_path = filedialog.asksaveasfilename(defaultextension=".wav")
    if save_path:
        wavfile.write(save_path, SAMPLE_RATE, output)
        messagebox.showinfo("Готово", "Файл стабильно закодирован")


def decode_file():
    filepath = filedialog.askopenfilename(filetypes=[("WAV files", "*.wav")])
    if not filepath:
        return

    samplerate, data = wavfile.read(filepath)

    if len(data.shape) > 1:
        data = data[:, 0]

    total_symbols = len(data) // samples_per_symbol
    bitstream = ""

    for i in range(total_symbols):
        chunk = data[i*samples_per_symbol:(i+1)*samples_per_symbol]

        fft = np.fft.fft(chunk)
        fft_freqs = np.fft.fftfreq(len(chunk), 1/SAMPLE_RATE)

        magnitudes = []

        for f in freqs:
            idx = np.argmin(np.abs(fft_freqs - f))
            magnitudes.append(np.abs(fft[idx]))

        magnitudes = np.array(magnitudes)
        threshold = np.max(magnitudes) * THRESHOLD_RATIO

        for mag in magnitudes:
            bitstream += "1" if mag > threshold else "0"

    bytes_out = []
    for i in range(0, len(bitstream), 8):
        byte = bitstream[i:i+8]
        if len(byte) == 8:
            bytes_out.append(int(byte, 2))

    data_bytes = bytes(bytes_out)

    file_size = struct.unpack("I", data_bytes[:4])[0]
    original_data = data_bytes[4:4+file_size]

    save_path = filedialog.asksaveasfilename()
    if save_path:
        with open(save_path, "wb") as f:
            f.write(original_data)
        messagebox.showinfo("Готово", "Файл успешно декодирован")


# ---------------- GUI ----------------

root = tk.Tk()
root.title("Stable Audio File Modem")
root.geometry("400x200")

tk.Label(root, text="Надёжная версия (128 частот, 40мс)",
         font=("Arial", 11)).pack(pady=10)

tk.Button(root, text="Кодировать файл → WAV",
          command=encode_file, height=2).pack(pady=5)

tk.Button(root, text="Декодировать WAV → файл",
          command=decode_file, height=2).pack(pady=5)

root.mainloop()