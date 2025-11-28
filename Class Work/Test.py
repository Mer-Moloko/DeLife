import numpy as np
from scipy.io import wavfile

# Параметры сигнала
sample_rate = 44100  # Частота дискретизации (Гц)
duration = 5         # Длительность сигнала (сек)
freq = 1000          # Основная частота (Гц)
amplitude = 0.8      # Амплитуда основного тона (0..1)

# Параметры гармоник для предискажения
h2_amplitude = 0.012  # Амплитуда 2-й гармоники (% от основной)
h3_amplitude = 0.018  # Амплитуда 3-й гармоники (% от основной)
h2_phase = np.pi      # Фаза 2-й гармоники (рад)
h3_phase = np.pi      # Фаза 3-й гармоники (рад)

# Расчет временной оси
t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)

# Генерация основного тона
main_signal = amplitude * np.sin(2 * np.pi * freq * t)

# Добавление гармоник с предискажением
harmonics = (
    h2_amplitude * np.sin(2 * np.pi * 2 * freq * t + h2_phase) +
    h3_amplitude * np.sin(2 * np.pi * 3 * freq * t + h3_phase)
)

# Комбинированный сигнал
output_signal = main_signal + harmonics

# Нормализация для предотвращения клиппинга
output_signal = output_signal / np.max(np.abs(output_signal))

# Сохранение в WAV-файл (16-битный PCM)
wavfile.write(
    "predistorted_1kHz.wav",
    sample_rate,
    (output_signal * 32767).astype(np.int16)
)

print("Файл 'predistorted_1kHz.wav' создан")
print("Параметры гармоник:")
print(f"Вторая гармоника: {h2_amplitude*100:.3f}%")
print(f"Третья гармоника: {h3_amplitude*100:.3f}%")