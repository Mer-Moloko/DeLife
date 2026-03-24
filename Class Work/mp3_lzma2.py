import tkinter as tk
from tkinter import filedialog, messagebox
import numpy as np
import wave
import sounddevice as sd
import threading
import io
import lzma

from scipy.fftpack import dct, idct
from scipy.signal import resample

# ================= Advanced TinyAudio Codec =================
class TinyAudioAdvanced:
    def __init__(self, codec_sr=16000, block_size=512, quant_levels=32,
                 normalize=True, volume=1.0, low_cut_db=5.0, freq_norm=True):
        self.codec_sr = codec_sr
        self.block_size = block_size
        self.quant_levels = quant_levels
        self.normalize = normalize
        self.volume = volume
        self.low_cut_db = low_cut_db
        self.freq_norm = freq_norm

    def set_quality(self, q):
        self.quant_levels = max(4, min(int(q), 64))

    def set_codec_sr(self, sr):
        self.codec_sr = int(sr)

    def set_normalize(self, flag):
        self.normalize = bool(flag)

    def set_freq_norm(self, flag):
        self.freq_norm = bool(flag)

    # ===================== Compress =====================
    def compress(self, wav_file, out_file):
        wav = wave.open(wav_file, 'rb')
        sr_in = wav.getframerate()
        ch = wav.getnchannels()
        audio = np.frombuffer(wav.readframes(wav.getnframes()), dtype=np.int16)
        wav.close()

        if ch == 2:
            audio = audio.reshape(-1, 2).mean(axis=1)

        audio = audio.astype(np.float32)

        # --------- Block prepare ---------
        n_blocks = int(np.ceil(len(audio) / self.block_size))
        padded = np.zeros(n_blocks * self.block_size, dtype=np.float32)
        padded[:len(audio)] = audio
        blocks = padded.reshape(n_blocks, self.block_size)

        # --------- Low frequency attenuation ---------
        if self.normalize:
            dct_blocks = dct(blocks, type=2, norm='ortho', axis=1)
            freqs = np.linspace(0, self.codec_sr / 2, self.block_size)
            low_mask = freqs < 150.0
            dct_blocks[:, low_mask] *= 10 ** (-self.low_cut_db / 20.0)
            blocks = idct(dct_blocks, type=2, norm='ortho', axis=1)

        audio = blocks.flatten()[:len(audio)]

        # --------- Resample ---------
        n_new = int(len(audio) * self.codec_sr / sr_in)
        audio = resample(audio, n_new)

        peak = np.max(np.abs(audio))
        if peak > 0:
            audio *= 32767.0 / peak

        # --------- DCT Compression ---------
        n_blocks = int(np.ceil(len(audio) / self.block_size))
        padded = np.zeros(n_blocks * self.block_size, dtype=np.float32)
        padded[:len(audio)] = audio
        blocks = padded.reshape(n_blocks, self.block_size)

        dct_blocks = dct(blocks, type=2, norm='ortho', axis=1)

        band_energy = None
        if self.freq_norm:
            band_energy = np.mean(np.abs(dct_blocks), axis=0) + 1e-9
            dct_blocks /= band_energy

        maxv = np.max(np.abs(dct_blocks), axis=1, keepdims=True) + 1e-9
        q = np.round(
            dct_blocks / maxv * (self.quant_levels // 2 - 1)
        ).astype(np.int8)

        # --------- NPZ → Memory ---------
        buf = io.BytesIO()
        np.savez(
            buf,
            q=q,
            maxv=maxv,
            band_energy=band_energy,
            n=len(audio),
            sr_in=sr_in,
            codec_sr=self.codec_sr,
            normalize=self.normalize,
            low_cut_db=self.low_cut_db,
            freq_norm=self.freq_norm,
            quant_levels=self.quant_levels
        )
        raw = buf.getvalue()

        # --------- LZMA2 compress (FORMAT_XZ) ---------
        compressed = lzma.compress(
            raw,
            format=lzma.FORMAT_XZ,
            preset=9 | lzma.PRESET_EXTREME
        )

        with open(out_file, "wb") as f:
            f.write(compressed)

    # ===================== Decompress =====================
    def decompress(self, in_file):
        with open(in_file, "rb") as f:
            compressed = f.read()

        raw = lzma.decompress(compressed)
        buf = io.BytesIO(raw)
        data = np.load(buf, allow_pickle=True)

        q = data['q']
        maxv = data['maxv'].astype(np.float32)
        band_energy = data.get('band_energy', None)

        n = int(data['n'])
        sr_in = int(data['sr_in'])

        self.codec_sr = int(data['codec_sr'])
        self.freq_norm = bool(data['freq_norm'])
        self.quant_levels = int(data['quant_levels'])

        dct_blocks = (
            q.astype(np.float32) /
            (self.quant_levels // 2 - 1)
        ) * maxv

        if self.freq_norm and band_energy is not None:
            dct_blocks *= band_energy

        blocks = idct(dct_blocks, type=2, norm='ortho', axis=1)
        audio = blocks.flatten()[:n]

        n_orig = int(n * sr_in / self.codec_sr)
        audio = resample(audio, n_orig)

        audio = np.clip(audio, -32768, 32767).astype(np.int16)
        return audio, sr_in


# ================= Audio Player =================
class AudioPlayer:
    def __init__(self):
        self.audio = None
        self.sr = 16000
        self.pos = 0
        self.playing = False
        self.stop_flag = False
        self.device = None

    def set_device(self, device_id):
        self.device = device_id

    def load(self, audio, sr):
        self.audio = audio.astype(np.int16)
        self.sr = sr
        self.pos = 0

    def play(self):
        if self.audio is None or self.playing:
            return
        self.playing = True
        self.stop_flag = False
        threading.Thread(target=self._thread, daemon=True).start()

    def _thread(self):
        chunk = 1024
        with sd.OutputStream(
            samplerate=self.sr,
            channels=1,
            dtype='float32',
            device=self.device
        ) as stream:
            while self.pos < len(self.audio) and not self.stop_flag:
                end = min(self.pos + chunk, len(self.audio))
                data = self.audio[self.pos:end].astype(np.float32) / 32768.0
                stream.write(data.reshape(-1, 1))
                self.pos = end
        self.playing = False

    def pause(self):
        self.stop_flag = True
        self.playing = False

    def stop(self):
        self.stop_flag = True
        self.pos = 0
        self.playing = False

    def rewind(self):
        self.pos = max(0, self.pos - 2048)

    def forward(self):
        self.pos = min(len(self.audio), self.pos + 2048)


# ================= Utils =================
def get_output_devices():
    return [(i, d['name']) for i, d in enumerate(sd.query_devices())
            if d['max_output_channels'] > 0]

def save_wav(filename, audio, sr):
    with wave.open(filename, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(audio.tobytes())


# ================= GUI =================
codec = TinyAudioAdvanced()
player = AudioPlayer()
decoded_audio = None
decoded_sr = None

root = tk.Tk()
root.title("TinyAudio Advanced Player")

# ---- Files ----
tk.Label(root, text="WAV файл:").grid(row=0, column=0)
entry_wav = tk.Entry(root, width=50)
entry_wav.grid(row=0, column=1)
tk.Button(
    root,
    text="Выбрать",
    command=lambda: entry_wav.delete(0, tk.END) or
    entry_wav.insert(0, filedialog.askopenfilename(filetypes=[("WAV files", "*.wav")]))
).grid(row=0, column=2)

tk.Label(root, text="TinyAudio файл:").grid(row=1, column=0)
entry_txt = tk.Entry(root, width=50)
entry_txt.grid(row=1, column=1)
tk.Button(
    root,
    text="Выбрать",
    command=lambda: entry_txt.delete(0, tk.END) or
    entry_txt.insert(0, filedialog.asksaveasfilename(defaultextension=".npz"))
).grid(row=1, column=2)

# ---- Codec params ----
quality_slider = tk.Scale(root, from_=4, to=64,
                          orient="horizontal", label="Качество")
quality_slider.set(32)
quality_slider.grid(row=2, column=0, columnspan=3)

tk.Label(root, text="Частота кодека (Hz):").grid(row=3, column=0)
codec_sr_entry = tk.Entry(root)
codec_sr_entry.insert(0, "16000")
codec_sr_entry.grid(row=3, column=1)

normalize_var = tk.IntVar(value=1)
tk.Checkbutton(root, text="Уменьшить НЧ на 5 дБ",
               variable=normalize_var).grid(row=3, column=2)

freq_norm_var = tk.IntVar(value=1)
tk.Checkbutton(root, text="Частотная нормализация",
               variable=freq_norm_var).grid(row=4, column=2)

# ---- Output device ----
tk.Label(root, text="Выходное устройство:").grid(row=4, column=0)
devices = get_output_devices()
device_var = tk.StringVar(value=f"{devices[0][0]}: {devices[0][1]}")
tk.OptionMenu(
    root,
    device_var,
    *[f"{i}: {n}" for i, n in devices]
).grid(row=4, column=1)

# ---- Player ----
slider = tk.Scale(root, from_=0, to=100,
                  orient="horizontal", length=400)
slider.grid(row=5, column=0, columnspan=3)

duration_label = tk.Label(root, text="Длительность: 0.00 сек")
duration_label.grid(row=6, column=0, columnspan=3)

# ================= Actions =================
def compress_action():
    try:
        codec.set_codec_sr(codec_sr_entry.get())
    except ValueError:
        messagebox.showerror("Ошибка", "Неверная частота")
        return

    codec.set_quality(quality_slider.get())
    codec.set_normalize(normalize_var.get())
    codec.set_freq_norm(freq_norm_var.get())

    codec.compress(entry_wav.get(), entry_txt.get())
    messagebox.showinfo("Готово", "Файл сжат (DCT + LZMA2)")

def load_and_play():
    def worker():
        global decoded_audio, decoded_sr
        decoded_audio, decoded_sr = codec.decompress(entry_txt.get())
        player.load(decoded_audio, decoded_sr)
        player.set_device(int(device_var.get().split(":")[0]))
        slider.config(to=len(decoded_audio))
        duration_label.config(
            text=f"Длительность: {len(decoded_audio)/decoded_sr:.2f} сек"
        )
        player.play()
        update_slider()
    threading.Thread(target=worker, daemon=True).start()

def save_decoded():
    if decoded_audio is None:
        return
    fname = filedialog.asksaveasfilename(defaultextension=".wav")
    if fname:
        save_wav(fname, decoded_audio, decoded_sr)

def update_slider():
    slider.set(player.pos)
    if player.playing:
        root.after(50, update_slider)

slider.config(command=lambda v: setattr(player, "pos", int(float(v))))

# ---- Buttons ----
tk.Button(root, text="Сжать WAV → TinyAudio",
          command=compress_action).grid(row=7, column=0)

tk.Button(root, text="Декодировать и воспроизвести",
          command=load_and_play).grid(row=7, column=1)

tk.Button(root, text="💾 Сохранить WAV",
          command=save_decoded).grid(row=7, column=2)

tk.Button(root, text="⏮", command=player.rewind).grid(row=8, column=0)
tk.Button(root, text="▶", command=lambda: [player.play(), update_slider()]).grid(row=8, column=1)
tk.Button(root, text="⏸", command=player.pause).grid(row=8, column=2)
tk.Button(root, text="⏹", command=lambda: [player.stop(), slider.set(0)]).grid(row=9, column=0)
tk.Button(root, text="⏭", command=player.forward).grid(row=9, column=1)

root.mainloop()
