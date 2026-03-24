import numpy as np
import wave

# ===== ПАРАМЕТРЫ =====
FS = 44100
BIT_DURATION = 0.02  # 20 мс = 50 бит/с
FREQ_0 = 3000        # логический 0
FREQ_1 = 1000        # логическая 1
AMPLITUDE = 0.9

PREAMBLE = "10101010" * 10  # синхронизация


def text_to_bits(text: str) -> str:
    data = text.encode("utf-8")
    return "".join(f"{byte:08b}" for byte in data)


def generate_tone(freq, duration, fs):
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    return np.sin(2 * np.pi * freq * t)


def encode_text_to_wav(input_txt, output_wav):
    with open(input_txt, "r", encoding="utf-8") as f:
        text = f.read()

    bits = PREAMBLE + text_to_bits(text)

    audio = np.zeros(0, dtype=np.float32)

    for bit in bits:
        freq = FREQ_1 if bit == "1" else FREQ_0
        tone = generate_tone(freq, BIT_DURATION, FS)
        audio = np.concatenate((audio, tone))

    # строгая нормализация без искажений
    audio *= AMPLITUDE / np.max(np.abs(audio))

    audio_int16 = (audio * 32767).astype(np.int16)

    with wave.open(output_wav, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(FS)
        wf.writeframes(audio_int16.tobytes())

if __name__ == "__main__":
    encode_text_to_wav("input.txt", "cassette_master.wav")
