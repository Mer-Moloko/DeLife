import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
import sounddevice as sd
import soundfile as sf


class CassettePreEmphasis:
    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate
        # Параметры пре-эмфазиса для компенсации потерь высоких частот
        self.f_preemp = 1000  # Частота пре-эмфазиса
        self.boost = 6.0  # Усиление высоких частот в dB

    def create_preemphasis_filter(self):
        """Создает фильтр предыскажения"""
        # Фильтр высоких частот для пре-эмфазиса
        f_norm = self.f_preemp / (self.sample_rate / 2)
        b, a = signal.butter(1, f_norm, btype='high', analog=False)
        return b, a

    def generate_1000hz_tone(self, duration=3.0, amplitude=0.8):
        """Генерирует тон 1000 ГЦ"""
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        tone = amplitude * np.sin(2 * np.pi * 1000 * t)
        return tone

    def apply_preemphasis(self, audio):
        """Применяет предыскажение к аудиосигналу"""
        b, a = self.create_preemphasis_filter()
        processed_audio = signal.lfilter(b, a, audio)
        return processed_audio

    def analyze_frequency_response(self):
        """Анализирует частотную характеристику фильтра"""
        b, a = self.create_preemphasis_filter()
        w, h = signal.freqz(b, a, worN=2000)
        frequencies = w * self.sample_rate / (2 * np.pi)
        magnitude_db = 20 * np.log10(np.abs(h))

        plt.figure(figsize=(10, 6))
        plt.semilogx(frequencies, magnitude_db)
        plt.title('Частотная характеристика фильтра предыскажения')
        plt.xlabel('Частота (Hz)')
        plt.ylabel('Усиление (dB)')
        plt.grid(True)
        plt.xlim(20, 20000)
        plt.ylim(-10, 10)
        plt.show()

        return frequencies, magnitude_db

    def play_processed_tone(self, duration=5.0):
        """Генерирует, обрабатывает и воспроизводит тон"""
        print("Генерация тона 1000 ГЦ...")
        original_tone = self.generate_1000hz_tone(duration)

        print("Применение предыскажения...")
        processed_tone = self.apply_preemphasis(original_tone)

        # Нормализация для предотвращения клиппинга
        processed_tone = processed_tone / np.max(np.abs(processed_tone)) * 0.8

        print("Воспроизведение обработанного тона...")
        sd.play(processed_tone, self.sample_rate)
        sd.wait()

        return original_tone, processed_tone

    def save_audio(self, audio, filename):
        """Сохраняет аудио в файл"""
        sf.write(filename, audio, self.sample_rate)
        print(f"Аудио сохранено в {filename}")


def main():
    # Создание экземпляра процессора
    processor = CassettePreEmphasis(sample_rate=44100)

    print("Анализатор предыскажения для Yamaha KX-300")
    print("=" * 50)

    # Анализ частотной характеристики
    print("Анализ частотной характеристики фильтра...")
    processor.analyze_frequency_response()

    # Генерация и воспроизведение тона
    original, processed = processor.play_processed_tone(duration=5)

    # Сохранение аудио
    processor.save_audio(processed, "preemphasized_1000hz.wav")
    processor.save_audio(original, "original_1000hz.wav")

    print("\nРекомендации по записи на Yamaha KX-300:")
    print("1. Используйте качественную хромовую или металлическую ленту")
    print("2. Установите уровень записи так, чтобы пики не превышали 0 dB")
    print("3. Предыскажение компенсирует потери высоких частот при записи")
    print("4. При воспроизведении используйте стандартную де-эмфазизацию 120 μs")


if __name__ == "__main__":
    main()