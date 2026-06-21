import tkinter as tk
from tkinter import filedialog, messagebox
import numpy as np
import wave
import os

SR = 44100
TONE_FREQ = 1000.0
MARKER_DURATION = 2.0
ATTACK_MS = 1.0
RELEASE_MS = 100.0
NOISE_FLOOR_DB = -30.0

MARKER_MINUS_30 = -30.0
MARKER_0 = 0.0

# ПРАВИЛЬНАЯ кривая кодирования (СЖАТИЕ)
# Вход (дБ) -> Выход (дБ)
# Цель: сжать динамический диапазон 100 дБ до ~30 дБ
ENCODE_DB_IN = np.array([-100, -80, -60, -40, -30, -20, -10, 0])
ENCODE_DB_OUT = np.array([-40, -38, -35, -30, -25, -18, -10, -3])

# Кривая декодирования (РАСШИРЕНИЕ) - обратная к ENCODE
DECODE_DB_IN = np.array([-40, -35, -30, -25, -18, -10, -3])
DECODE_DB_OUT = np.array([-100, -60, -40, -30, -20, -10, 0])


def db_to_linear(db):
    return 10.0 ** (db / 20.0)


def linear_to_db(lin):
    if lin < 1e-12:
        return -200.0
    return 20.0 * np.log10(lin)


def read_wav_safe(filepath):
    try:
        from scipy.io import wavfile
        sr, data = wavfile.read(filepath)
    except:
        with wave.open(filepath, 'rb') as wav:
            sr = wav.getframerate()
            n_channels = wav.getnchannels()
            n_frames = wav.getnframes()
            raw_data = wav.readframes(n_frames)
            data = np.frombuffer(raw_data, dtype=np.int16)
            if n_channels == 2:
                data = data.reshape(-1, 2)
            else:
                data = data.reshape(-1, 1)

    if data.dtype == np.int16:
        data = data.astype(np.float32) / 32768.0
    elif data.dtype == np.int32:
        data = data.astype(np.float32) / 2147483648.0

    if data.ndim == 1:
        data = data.reshape(-1, 1)

    return sr, data


def write_wav_safe(filepath, sr, data):
    if data.ndim == 1:
        data = data.reshape(-1, 1)

    data = np.clip(data, -1.0, 1.0)
    data_int = (data * 32767.0).astype(np.int16)

    with wave.open(filepath, 'wb') as wav:
        wav.setnchannels(data.shape[1])
        wav.setsampwidth(2)
        wav.setframerate(sr)
        wav.writeframes(data_int.tobytes())


def get_peak_level(data, start_sample, duration_samples):
    end_sample = min(start_sample + duration_samples, data.shape[0])
    if start_sample >= data.shape[0]:
        return -200.0
    segment = data[start_sample:end_sample, :]
    peak = np.max(np.abs(segment))
    if peak < 1e-12:
        return -200.0
    return linear_to_db(peak)


def generate_tone(sr, duration, freq, amplitude):
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    return amplitude * np.sin(2 * np.pi * freq * t)


def apply_compression(data, sr, map_func):
    """
    Применяет сжатие/расширение с пиковым детектором
    """
    n_samples = data.shape[0]
    n_channels = data.shape[1]
    block_size = max(1, int(sr * 0.001))  # 1 мс

    attack_coef = np.exp(-1.0 / (sr * ATTACK_MS / 1000.0))
    release_coef = np.exp(-1.0 / (sr * RELEASE_MS / 1000.0))

    out = np.zeros_like(data)
    peak = 0.0

    for i in range(0, n_samples, block_size):
        end = min(i + block_size, n_samples)
        block = data[i:end, :]

        # Находим пик в блоке
        block_peak = np.max(np.abs(block))

        # Пиковый детектор
        if block_peak > peak:
            peak = peak * attack_coef + block_peak * (1 - attack_coef)
        else:
            peak = peak * release_coef + block_peak * (1 - release_coef)

        # Применяем преобразование
        if peak > 1e-12:
            in_db = linear_to_db(peak)
            out_db = map_func(in_db)

            # Вычисляем усиление
            gain_db = out_db - in_db
            gain_lin = db_to_linear(gain_db)
        else:
            gain_lin = 0.0

        # Применяем усиление ко всему блоку
        out[i:end, :] = block * gain_lin

    return out


def apply_noise_gate(data, threshold_db):
    """Шумовой порог: всё, что ниже threshold_db, становится тишиной"""
    n_samples = data.shape[0]
    n_channels = data.shape[1]
    block_size = max(1, int(SR * 0.001))

    out = np.zeros_like(data)

    for i in range(0, n_samples, block_size):
        end = min(i + block_size, n_samples)
        block = data[i:end, :]

        # Пик в блоке
        block_peak = np.max(np.abs(block))

        if block_peak > 1e-12:
            peak_db = linear_to_db(block_peak)
            if peak_db < threshold_db:
                out[i:end, :] = 0.0
            else:
                out[i:end, :] = block
        else:
            out[i:end, :] = 0.0

    return out


def encode_file(input_path, output_path=None):
    sr, data = read_wav_safe(input_path)

    print(f"Encoding: {data.shape[0]} samples, {data.shape[1]} channels")

    # Проверяем уровень сигнала ДО кодирования
    peak_before = get_peak_level(data, 0, min(44100, data.shape[0]))
    print(f"Peak BEFORE encoding: {peak_before:.1f} dB")

    # Генерируем метки
    marker_minus30 = generate_tone(sr, MARKER_DURATION, TONE_FREQ, db_to_linear(MARKER_MINUS_30))
    marker_0 = generate_tone(sr, MARKER_DURATION, TONE_FREQ, db_to_linear(MARKER_0))
    silence = np.zeros(int(sr * 0.5))

    if data.shape[1] == 2:
        marker_minus30 = np.column_stack([marker_minus30, marker_minus30])
        marker_0 = np.column_stack([marker_0, marker_0])
        silence = np.column_stack([silence, silence])
    else:
        marker_minus30 = marker_minus30.reshape(-1, 1)
        marker_0 = marker_0.reshape(-1, 1)
        silence = silence.reshape(-1, 1)

    # Кодирование (сжатие)
    def encode_map(in_db):
        return np.interp(in_db, ENCODE_DB_IN, ENCODE_DB_OUT)

    processed = apply_compression(data, sr, encode_map)

    # Проверяем уровень ПОСЛЕ кодирования
    peak_after = get_peak_level(processed, 0, min(44100, processed.shape[0]))
    print(f"Peak AFTER encoding: {peak_after:.1f} dB")

    # Объединяем
    result = np.vstack([
        marker_minus30,
        silence,
        marker_0,
        silence,
        processed
    ])

    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = base + "_encoded.wav"

    write_wav_safe(output_path, sr, result)
    print(f"Encoded: {result.shape[0]} samples")
    return output_path


def decode_file(input_path, output_path=None):
    sr, data = read_wav_safe(input_path)

    print(f"Decoding: {data.shape[0]} samples, {data.shape[1]} channels")

    marker_samples = int(sr * MARKER_DURATION)
    silence_samples = int(sr * 0.5)

    # Позиции
    pos_marker1 = 0
    pos_silence1 = pos_marker1 + marker_samples
    pos_marker2 = pos_silence1 + silence_samples
    pos_silence2 = pos_marker2 + marker_samples
    pos_signal = pos_silence2 + silence_samples

    print(f"Marker1: {pos_marker1}-{pos_marker1 + marker_samples}")
    print(f"Marker2: {pos_marker2}-{pos_marker2 + marker_samples}")
    print(f"Signal start: {pos_signal}")

    if data.shape[0] < pos_signal:
        messagebox.showerror("Error", "File too short!")
        return None

    # Измеряем метки
    level_minus30 = get_peak_level(data, pos_marker1, marker_samples)
    level_0 = get_peak_level(data, pos_marker2, marker_samples)

    print(f"Marker -30 dB level: {level_minus30:.1f} dB")
    print(f"Marker 0 dB level: {level_0:.1f} dB")

    # Калибровка
    if level_minus30 > -100.0:
        calibration_gain = db_to_linear(MARKER_MINUS_30 - level_minus30)
        print(f"Calibration gain: {linear_to_db(calibration_gain):.1f} dB")
    else:
        calibration_gain = 1.0

    # Извлекаем сигнал
    audio = data[pos_signal:, :]
    print(f"Signal extracted: {audio.shape[0]} samples")

    if audio.shape[0] == 0:
        messagebox.showerror("Error", "No audio data found")
        return None

    # Калибруем
    audio = audio * calibration_gain

    # Декодирование (расширение)
    def decode_map(in_db):
        return np.interp(in_db, DECODE_DB_IN, DECODE_DB_OUT)

    print("Applying expansion...")
    expanded = apply_compression(audio, sr, decode_map)

    # Проверяем уровень после расширения
    expanded_peak = get_peak_level(expanded, 0, min(44100, expanded.shape[0]))
    print(f"Expanded peak: {expanded_peak:.1f} dB")

    # Шумовой порог
    print(f"Applying noise gate at {NOISE_FLOOR_DB} dB...")
    processed = apply_noise_gate(expanded, NOISE_FLOOR_DB)

    # Проверяем финальный уровень
    final_peak = get_peak_level(processed, 0, min(44100, processed.shape[0]))
    print(f"Final peak: {final_peak:.1f} dB")

    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = base + "_decoded.wav"

    write_wav_safe(output_path, sr, processed)
    print(f"Decoded: {processed.shape[0]} samples")
    return output_path


class App:
    def __init__(self, root):
        self.root = root
        root.title("Audio Compander - PROPER COMPRESSION")
        self.file_path = tk.StringVar()
        self.status = tk.StringVar(value="Ready")

        tk.Label(root, text="File:").grid(row=0, column=0, padx=5, pady=5)
        tk.Entry(root, textvariable=self.file_path, width=50).grid(row=0, column=1, padx=5, pady=5)
        tk.Button(root, text="Browse", command=self.browse_file).grid(row=0, column=2, padx=5, pady=5)

        tk.Button(root, text="Encode", command=self.encode, width=12, bg="lightblue").grid(row=1, column=0, padx=5,
                                                                                           pady=5)
        tk.Button(root, text="Decode", command=self.decode, width=12, bg="lightgreen").grid(row=1, column=1, padx=5,
                                                                                            pady=5)
        tk.Button(root, text="Exit", command=self.root.quit, width=12).grid(row=1, column=2, padx=5, pady=5)

        tk.Label(root, textvariable=self.status, relief=tk.SUNKEN, anchor=tk.W, width=60).grid(
            row=2, column=0, columnspan=3, padx=5, pady=10, sticky="ew"
        )

        info = tk.Label(root, text="Compression: -100dB -> -40dB | 0dB -> -3dB", font=("Arial", 8))
        info.grid(row=3, column=0, columnspan=3, pady=5)

    def browse_file(self):
        f = filedialog.askopenfilename(filetypes=[("WAV files", "*.wav")])
        if f:
            self.file_path.set(f)
            self.status.set("Selected: " + os.path.basename(f))

    def encode(self):
        if not self.file_path.get():
            messagebox.showerror("Error", "Select a file")
            return
        try:
            self.status.set("Encoding...")
            self.root.update()
            out = encode_file(self.file_path.get())
            self.status.set("Done: " + os.path.basename(out))
            messagebox.showinfo("Success", "Encoding complete:\n" + out)
        except Exception as e:
            self.status.set("Error: " + str(e))
            messagebox.showerror("Error", str(e))

    def decode(self):
        if not self.file_path.get():
            messagebox.showerror("Error", "Select a file")
            return
        try:
            self.status.set("Decoding...")
            self.root.update()
            out = decode_file(self.file_path.get())
            if out:
                self.status.set("Done: " + os.path.basename(out))
                messagebox.showinfo("Success", "Decoding complete:\n" + out)
        except Exception as e:
            self.status.set("Error: " + str(e))
            messagebox.showerror("Error", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()