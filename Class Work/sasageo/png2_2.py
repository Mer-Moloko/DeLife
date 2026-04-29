#!/usr/bin/env python3
# resilient_png_tool_v4.py
"""
Resilient PNG tool v4
- Adds tape-friendly block-based compression with optional parity for robustness
- Allows LZ4 or Zstandard compression algorithms (if available)
- GUI controls: algorithm, level, tape mode, block size, parity
- All previous features preserved: lossy/lossless, .fj4 container with meta JSON, editable metadata, backup, PNG chunk analysis
"""
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from PIL import Image, ImageTk
import io
import os
import struct
import hashlib
import re
import sys
import json
import shutil
import binascii
import threading
import time
from typing import Optional, Tuple, List

from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.fernet import Fernet
import base64, os

# optional compression libs
try:
    import lz4.frame as lz4frame
except Exception:
    lz4frame = None

try:
    import zstandard as zstd
except Exception:
    zstd = None

MAGIC = b"FJ4\x00"
VERSION = 1
HEX_PAIR_RE = re.compile(rb"[0-9A-Fa-f]{2}")

# ------------------------------
# Utilities
# ------------------------------
def sha256_bytes(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()

def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def md5_hex(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()

def safe_copy_backup(path: str) -> Optional[str]:
    if not os.path.exists(path):
        return None
    bak_path = path + ".bak"
    try:
        if not os.path.exists(bak_path):
            shutil.copy2(path, bak_path)
        return bak_path
    except Exception:
        return None
        

# Crypto
def derive_key_from_password(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=200000)
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

def encrypt_meta_dict(meta: dict, password: str) -> dict:
    salt = os.urandom(16)
    key = derive_key_from_password(password, salt)
    f = Fernet(key)
    meta_json = json.dumps(meta, ensure_ascii=False).encode('utf-8')
    token = f.encrypt(meta_json)  # bytes
    return {
        "_meta_cipher": "fernet",
        "_meta_salt": base64.b64encode(salt).decode('ascii'),
        "_meta_token": base64.b64encode(token).decode('ascii')
    }

def decrypt_meta_dict(encrypted_meta_obj: dict, password: str) -> dict:
    salt = base64.b64decode(encrypted_meta_obj["_meta_salt"])
    token = base64.b64decode(encrypted_meta_obj["_meta_token"])
    key = derive_key_from_password(password, salt)
    f = Fernet(key)
    meta_json = f.decrypt(token)
    return json.loads(meta_json.decode('utf-8'))

# ------------------------------
# Image functions
# ------------------------------
def encode_image_lossy_to_text(image_path: str) -> Tuple[bytes, int, int]:
    img = Image.open(image_path).convert("RGB")
    img = img.resize((max(1, img.width // 2), max(1, img.height // 2)))
    img = img.convert("L")
    width, height = img.size
    pixels = list(img.getdata())
    lines = [f"{width} {height}"]
    for y in range(height):
        row_pixels = pixels[y * width:(y + 1) * width]
        hex_row = "".join(f"{p:02X}" for p in row_pixels)
        lines.append(hex_row)
    text = "\n".join(lines)
    return text.encode("ascii"), width, height

def reconstruct_image_from_text_bytes(text_bytes: bytes) -> Image.Image:
    text = text_bytes.decode("ascii", errors="ignore")
    lines = text.splitlines()
    if not lines:
        raise ValueError("Empty textual payload")
    parts = lines[0].strip().split()
    if len(parts) < 2:
        raise ValueError("Missing width/height header")
    width, height = int(parts[0]), int(parts[1])
    img = Image.new("L", (width, height))
    for y in range(min(height, len(lines) - 1)):
        ln = lines[1 + y]
        hex_pairs = re.findall(r"[0-9A-Fa-f]{2}", ln)
        row_vals = [int(h, 16) for h in hex_pairs]
        for x, v in enumerate(row_vals[:width]):
            img.putpixel((x, y), v)
    return img

# ------------------------------
# Container pack/unpack
# ------------------------------
def pack_container(payload: bytes, compressed: bool, mode_lossy: bool, metadata: dict) -> bytes:
    flags = 0
    if compressed:
        flags |= 1
    if mode_lossy:
        flags |= 2
    meta_json = json.dumps(metadata, ensure_ascii=False).encode("utf-8")
    meta_len = len(meta_json)
    payload_len = len(payload)
    sha = sha256_bytes(payload)
    header = (
        MAGIC
        + struct.pack(">B B H", VERSION, flags, 0)
        + struct.pack(">Q", meta_len)
        + struct.pack(">Q", payload_len)
        + sha
    )
    return header + meta_json + payload

def unpack_container(data: bytes) -> dict:
    if len(data) < 4 or data[:4] != MAGIC:
        raise ValueError("Not a valid FJ4 container (magic mismatch)")
    idx = 4
    if len(data) < idx + 1 + 1 + 2 + 8 + 8 + 32:
        raise ValueError("Container too small")
    version = data[idx]; idx += 1
    flags = data[idx]; idx += 1
    reserved = struct.unpack(">H", data[idx:idx+2])[0]; idx += 2
    meta_len = struct.unpack(">Q", data[idx:idx+8])[0]; idx += 8
    payload_len = struct.unpack(">Q", data[idx:idx+8])[0]; idx += 8
    sha = data[idx:idx+32]; idx += 32
    truncated = len(data) < idx + meta_len + payload_len
    meta_bytes = data[idx: idx + meta_len]
    idx += meta_len
    payload = data[idx: idx + payload_len]
    try:
        meta_obj = json.loads(meta_bytes.decode("utf-8")) if meta_bytes else {}
    except Exception:
        meta_obj = {"_raw_meta_bytes_preview": meta_bytes[:200].decode("utf-8", errors="ignore")}
    return {
        "version": version,
        "flags": flags,
        "compressed": bool(flags & 1),
        "mode_lossy": bool(flags & 2),
        "meta_len": meta_len,
        "payload_len": payload_len,
        "sha256": sha,
        "meta": meta_obj,
        "payload": payload,
        "truncated": truncated
    }

# ------------------------------
# Compression wrappers
# ------------------------------
def compress_block_lz4(data: bytes) -> bytes:
    if lz4frame is None:
        raise RuntimeError("lz4.frame not available. Install python-lz4")
    return lz4frame.compress(data)

def decompress_block_lz4(data: bytes) -> bytes:
    if lz4frame is None:
        raise RuntimeError("lz4.frame not available. Install python-lz4")
    return lz4frame.decompress(data)

def compress_block_zstd(data: bytes, level: int) -> bytes:
    if zstd is None:
        raise RuntimeError("zstandard not available. Install zstandard")
    cctx = zstd.ZstdCompressor(level=level)
    return cctx.compress(data)

def decompress_block_zstd(data: bytes) -> bytes:
    if zstd is None:
        raise RuntimeError("zstandard not available. Install zstandard")
    dctx = zstd.ZstdDecompressor()
    return dctx.decompress(data)

# ------------------------------
# Tape-mode helpers (block-based compression + parity)
# ------------------------------
def create_tape_payload(payload: bytes, algo: str, level: int, block_size: int, parity_count: int):
    """
    Split payload into blocks, compress each block with chosen algo/level,
    pad compressed blocks to max_length and compute parity_count XOR parity blocks (if parity_count==1).
    Returns: combined_payload_bytes, metadata_dict with per-block info
    """
    if algo not in ("lz4", "zstd"):
        raise ValueError("Unknown algorithm")
    blocks = [payload[i:i+block_size] for i in range(0, len(payload), block_size)]
    compressed_blocks = []
    compressed_lengths = []
    block_sha256s = []
    for b in blocks:
        if algo == "lz4":
            cb = compress_block_lz4(b)
        else:
            cb = compress_block_zstd(b, level=level)
        compressed_blocks.append(cb)
        compressed_lengths.append(len(cb))
        block_sha256s.append(sha256_hex(cb))
    # pad compressed blocks to max length for XOR parity
    maxlen = max(len(x) for x in compressed_blocks) if compressed_blocks else 0
    padded_blocks = [cb + b"\x00" * (maxlen - len(cb)) for cb in compressed_blocks]
    parity_blocks = []
    if parity_count and parity_count > 0:
        # simple single XOR parity block (can recover single missing block)
        # For parity_count>1 we would need more advanced scheme — not implemented
        parity = bytearray(maxlen)
        for pb in padded_blocks:
            for i, val in enumerate(pb):
                parity[i] ^= val
        parity_blocks.append(bytes(parity))
    # build combined payload: all padded compressed blocks concatenated, then parity blocks concatenated
    combined = b"".join(padded_blocks) + b"".join(parity_blocks)
    # metadata describing blocks
    meta = {
        "tape_mode": True,
        "block_size": block_size,
        "block_count": len(blocks),
        "block_compressed_lengths": compressed_lengths,
        "block_sha256s": block_sha256s,
        "padded_block_length": maxlen,
        "parity_count": len(parity_blocks),
        "compression_algo": algo,
        "compression_level": level
    }
    return combined, meta

def recover_tape_payload_from_combined(combined: bytes, meta: dict):
    """
    Given combined bytes (padded compressed blocks + parity blocks) and meta, attempt recovery:
    - slice padded blocks
    - verify sha256 for each (using stored compressed_lengths to extract original cb)
    - if one block fails and parity_count==1, reconstruct it via XOR parity block
    - decompress each block and concatenate to original payload
    Returns: (success_bool, recovered_payload_bytes, diagnostics)
    """
    diagnostics = {}
    block_count = meta.get("block_count", 0)
    padded_len = meta.get("padded_block_length", 0)
    parity_count = meta.get("parity_count", 0)
    compressed_lengths = meta.get("block_compressed_lengths", [])
    stored_shas = meta.get("block_sha256s", [])
    algo = meta.get("compression_algo", "lz4")
    level = meta.get("compression_level", 0)
    expected_total_blocks_bytes = block_count * padded_len
    if len(combined) < expected_total_blocks_bytes:
        return False, None, {"error": "combined payload too small for declared blocks"}
    padded_blocks_data = combined[:expected_total_blocks_bytes]
    parity_data = combined[expected_total_blocks_bytes:]
    # slice padded blocks
    padded_blocks = [padded_blocks_data[i*padded_len:(i+1)*padded_len] for i in range(block_count)]
    # extract actual compressed bytes via compressed_lengths
    compressed_blocks = []
    corrupt_indices = []
    for i, pb in enumerate(padded_blocks):
        clen = compressed_lengths[i] if i < len(compressed_lengths) else padded_len
        cb = pb[:clen]
        compressed_blocks.append(cb)
        sha = sha256_hex(cb)
        expected_sha = stored_shas[i] if i < len(stored_shas) else None
        if expected_sha is not None and sha != expected_sha:
            corrupt_indices.append(i)
    diagnostics["corrupt_indices_initial"] = corrupt_indices.copy()
    # try recover if exactly one corrupt and parity_count >=1
    if corrupt_indices and parity_count >= 1:
        if len(corrupt_indices) == 1 and len(parity_data) >= padded_len:
            # parity block is the first parity_count* padded_len bytes of parity_data
            parity_block = parity_data[:padded_len]
            # XOR parity with all other padded blocks -> yields padded data of missing block
            recovered = bytearray(padded_len)
            for i in range(padded_len):
                v = parity_block[i]
                for j, pb in enumerate(padded_blocks):
                    if j == corrupt_indices[0]:
                        continue
                    v ^= pb[i]
                recovered[i] = v
            # take recovered compressed bytes (truncate to expected compressed length)
            rec_clen = compressed_lengths[corrupt_indices[0]]
            rec_cb = bytes(recovered[:rec_clen])
            # verify sha
            rec_sha = sha256_hex(rec_cb)
            if rec_sha == stored_shas[corrupt_indices[0]]:
                compressed_blocks[corrupt_indices[0]] = rec_cb
                diagnostics["recovered_index"] = corrupt_indices[0]
                corrupt_indices = []
            else:
                diagnostics["recovery_failed_sha_mismatch"] = True
        else:
            diagnostics["recovery_not_possible"] = "more than one corrupt or parity missing"
    # if still corrupt -> fail
    if corrupt_indices:
        diagnostics["final_corrupt_indices"] = corrupt_indices
        return False, None, diagnostics
    # decompress blocks and concatenate
    out_parts = []
    for i, cb in enumerate(compressed_blocks):
        try:
            if algo == "lz4":
                part = decompress_block_lz4(cb)
            else:
                part = decompress_block_zstd(cb)
            out_parts.append(part)
        except Exception as e:
            diagnostics.setdefault("decompress_errors", {})[i] = str(e)
            return False, None, diagnostics
    recovered_payload = b"".join(out_parts)
    diagnostics["success"] = True
    return True, recovered_payload, diagnostics

# ------------------------------
# PNG chunk analysis
# ------------------------------
def analyze_png_bytes(data: bytes) -> List[dict]:
    sig = b"\x89PNG\r\n\x1a\n"
    chunks = []
    if len(data) < len(sig) or data[:8] != sig:
        raise ValueError("Not a valid PNG signature")
    idx = 8
    while True:
        if idx + 8 > len(data):
            break
        chunk_offset = idx
        length = struct.unpack(">I", data[idx:idx+4])[0]
        idx += 4
        ctype = data[idx:idx+4]; idx += 4
        if idx + length + 4 > len(data):
            available = len(data) - idx
            chunks.append({
                "name": ctype.decode("ascii", errors="ignore"),
                "chunk_offset": chunk_offset,
                "length": length,
                "available_bytes": available,
                "crc_expected": None,
                "crc_actual": None,
                "crc_ok": False,
                "truncated": True,
                "chunk_end_offset": len(data)-1
            })
            break
        chunk_data = data[idx: idx + length]
        idx += length
        crc_expected = struct.unpack(">I", data[idx:idx+4])[0]
        idx += 4
        crc_calc = binascii.crc32(ctype + chunk_data) & 0xffffffff
        chunks.append({
            "name": ctype.decode("ascii", errors="ignore"),
            "chunk_offset": chunk_offset,
            "length": length,
            "crc_expected": crc_expected,
            "crc_actual": crc_calc,
            "crc_ok": (crc_calc == crc_expected),
            "truncated": False,
            "chunk_end_offset": idx - 1
        })
        if ctype == b'IEND':
            break
    return chunks

def find_corrupt_png_chunk(data: bytes) -> Optional[dict]:
    try:
        chunks = analyze_png_bytes(data)
    except Exception:
        return None
    for ch in chunks:
        if ch.get("truncated", False) or not ch.get("crc_ok", True):
            return ch
    return None

# ------------------------------
# LZ4 corruption heuristic (binary search)
# ------------------------------
def find_first_corrupt_offset_in_lz4_frame(frame_bytes: bytes) -> Optional[int]:
    if lz4frame is None:
        return None
    try:
        _ = lz4frame.decompress(frame_bytes)
        return None
    except Exception:
        pass
    good = 0
    for trial in [len(frame_bytes)//8, len(frame_bytes)//4, len(frame_bytes)//2]:
        if trial <= 0:
            continue
        try:
            _ = lz4frame.decompress(frame_bytes[:trial])
            good = trial
            break
        except Exception:
            continue
    if good == 0:
        return 0
    lo = good
    hi = len(frame_bytes)
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        try:
            _ = lz4frame.decompress(frame_bytes[:mid])
            lo = mid
        except Exception:
            hi = mid
    return hi

# ------------------------------
# Progress dialog
# ------------------------------
class ProgressDialog:
    def __init__(self, parent, title="Working...", message="Please wait"):
        self.top = tk.Toplevel(parent)
        self.top.title(title)
        self.top.resizable(False, False)
        self.top.transient(parent)
        self.top.grab_set()
        ttk.Label(self.top, text=message).pack(padx=10, pady=(10, 4))
        self.pb = ttk.Progressbar(self.top, mode="indeterminate", length=360)
        self.pb.pack(padx=10, pady=(4, 10))
        self.pb.start(20)
        parent.update_idletasks()
        try:
            w = parent.winfo_width(); h = parent.winfo_height()
            x = parent.winfo_rootx() + (w // 2) - 200
            y = parent.winfo_rooty() + (h // 2) - 40
            self.top.geometry(f"+{x}+{y}")
        except Exception:
            pass
    def close(self):
        try:
            self.pb.stop()
            self.top.grab_release()
            self.top.destroy()
        except Exception:
            pass

# ------------------------------
# GUI App
# ------------------------------
class App:
    def __init__(self, root):
        self.root = root
        root.title("Resilient PNG Encoder v4 (Tape-optimized)")
        self.current_image: Optional[Image.Image] = None
        self.current_image_path: Optional[str] = None
        self.current_container_path: Optional[str] = None
        self.loaded_metadata: dict = {}
        self._build_ui()

    def _build_ui(self):
        menubar = tk.Menu(self.root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open PNG...", command=self.open_image)
        filemenu.add_command(label="Open .fj4 / TXT...", command=self.open_container)
        filemenu.add_separator()
        filemenu.add_command(label="Save as TXT (lossy)", command=self.save_as_txt)
        filemenu.add_command(label="Save as .fj4 (lossy)", command=lambda: self.save_as_fj4(lossy=True))
        filemenu.add_command(label="Save as .fj4 (lossless)", command=lambda: self.save_as_fj4(lossy=False))
        filemenu.add_separator()
        filemenu.add_command(label="Import metadata JSON...", command=self.import_metadata_json)
        filemenu.add_command(label="Export metadata JSON...", command=self.export_metadata_json)
        filemenu.add_separator()
        filemenu.add_command(label="Save metadata into container", command=self.save_metadata_into_container)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=filemenu)
        self.root.config(menu=menubar)

        main = ttk.Frame(self.root)
        main.pack(fill="both", expand=True)

        left = ttk.Frame(main, width=380)
        left.pack(side="left", fill="y")

        right = ttk.Frame(main)
        right.pack(side="right", fill="both", expand=True)

        # Controls: compression algo, level, tape mode, block size, parity
        ctrl_label = ttk.Label(left, text="Compression / Tape options", font=("TkDefaultFont", 12, "bold"))
        ctrl_label.pack(anchor="nw", padx=6, pady=(6,0))

        ctrl_frame = ttk.Frame(left)
        ctrl_frame.pack(fill="x", padx=6, pady=6)

        ttk.Label(ctrl_frame, text="Algorithm:").grid(row=0, column=0, sticky="w")
        alg_values = ["lz4"]
        if zstd is not None:
            alg_values.append("zstd")
        self.alg_var = tk.StringVar(value=alg_values[0])
        self.alg_combo = ttk.Combobox(ctrl_frame, values=alg_values, textvariable=self.alg_var, state="readonly", width=10)
        self.alg_combo.grid(row=0, column=1, sticky="w", padx=6)

        ttk.Label(ctrl_frame, text="Level:").grid(row=0, column=2, sticky="w", padx=(10,0))
        self.level_var = tk.IntVar(value=3)
        self.level_spin = ttk.Spinbox(ctrl_frame, from_=1, to=22, textvariable=self.level_var, width=5)  # zstd up to 22
        self.level_spin.grid(row=0, column=3, sticky="w", padx=6)

        self.tape_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(ctrl_frame, text="Tape-friendly mode (block based)", variable=self.tape_var).grid(row=1, column=0, columnspan=4, sticky="w", pady=(6,0))

        ttk.Label(ctrl_frame, text="Block size (KB):").grid(row=2, column=0, sticky="w", pady=(6,0))
        self.blocksize_var = tk.IntVar(value=64)
        self.blocksize_spin = ttk.Spinbox(ctrl_frame, from_=1, to=1024, textvariable=self.blocksize_var, width=8)
        self.blocksize_spin.grid(row=2, column=1, sticky="w", padx=6, pady=(6,0))

        self.parity_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(ctrl_frame, text="Enable 1 parity block (recover single block)", variable=self.parity_var).grid(row=2, column=2, columnspan=2, sticky="w", padx=(10,0), pady=(6,0))

        # Metadata editable
        meta_label = ttk.Label(left, text="Metadata (editable JSON)", font=("TkDefaultFont", 12, "bold"))
        meta_label.pack(anchor="nw", padx=6, pady=(8,0))
        self.meta_text = tk.Text(left, width=48, height=18)
        self.meta_text.pack(padx=6, pady=6)
        meta_btns = ttk.Frame(left)
        meta_btns.pack(fill="x", padx=6, pady=(0,6))
        ttk.Button(meta_btns, text="Import JSON", command=self.import_metadata_json).pack(side="left", expand=True, fill="x")
        ttk.Button(meta_btns, text="Export JSON", command=self.export_metadata_json).pack(side="left", expand=True, fill="x")
        ttk.Button(meta_btns, text="Save metadata into container", command=self.save_metadata_into_container).pack(side="left", expand=True, fill="x")

        # Canvas right
        self.canvas_frame = ttk.Frame(right)
        self.canvas_frame.pack(fill="both", expand=True)
        self.vbar = ttk.Scrollbar(self.canvas_frame, orient="vertical")
        self.hbar = ttk.Scrollbar(self.canvas_frame, orient="horizontal")
        self.canvas = tk.Canvas(self.canvas_frame, bd=0, highlightthickness=0, xscrollcommand=self.hbar.set, yscrollcommand=self.vbar.set, background="#222")
        self.hbar.config(command=self.canvas.xview)
        self.vbar.config(command=self.canvas.yview)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vbar.grid(row=0, column=1, sticky="ns")
        self.hbar.grid(row=1, column=0, sticky="ew")
        self.canvas_frame.rowconfigure(0, weight=1)
        self.canvas_frame.columnconfigure(0, weight=1)

        # status
        self.status = tk.StringVar(value="Ready")
        ttk.Label(self.root, textvariable=self.status, relief="sunken", anchor="w").pack(fill="x", side="bottom")

    def set_status(self, txt: str):
        self.status.set(txt)
        self.root.update_idletasks()

    def display_image(self, pil_image: Image.Image):
        self.canvas.delete("all")
        self.img_for_tk = ImageTk.PhotoImage(pil_image)
        self.canvas.create_image(0, 0, anchor="nw", image=self.img_for_tk)
        self.canvas.config(scrollregion=(0, 0, pil_image.width, pil_image.height))
        self.set_status(f"Displayed {pil_image.width} x {pil_image.height}")

    def _write_meta_text(self, meta_obj: dict):
        try:
            pretty = json.dumps(meta_obj, ensure_ascii=False, indent=2)
        except Exception:
            pretty = str(meta_obj)
        self.meta_text.delete("1.0", "end")
        self.meta_text.insert("1.0", pretty)

    # ---------------
    # File operations
    # ---------------
    def open_image(self):
        path = filedialog.askopenfilename(filetypes=[("PNG files", "*.png"), ("All files", "*.*")])
        if not path:
            return
        def worker():
            pd = ProgressDialog(self.root, title="Opening", message=f"Opening {os.path.basename(path)}")
            try:
                with open(path, "rb") as f:
                    data = f.read()
                img = Image.open(io.BytesIO(data))
                corrupt_chunk = None
                try:
                    corrupt_chunk = find_corrupt_png_chunk(data)
                except Exception:
                    corrupt_chunk = None
                meta = {
                    "path": path,
                    "format": img.format,
                    "mode": img.mode,
                    "width": img.width,
                    "height": img.height,
                    "file_size": len(data),
                    "sha256": sha256_hex(data),
                    "md5": md5_hex(data),
                    "png_corrupt_chunk": corrupt_chunk
                }
                def ui_update():
                    self.current_image = img.copy()
                    self.current_image_path = path
                    self.current_container_path = None
                    self.display_image(self.current_image)
                    self.loaded_metadata = meta
                    self._write_meta_text(self.loaded_metadata)
                    if corrupt_chunk:
                        off = corrupt_chunk.get("chunk_offset")
                        name = corrupt_chunk.get("name")
                        instr = (
                            f"\n\nInstruction: Corrupted chunk '{name}' at byte offset {off} (decimal), "
                            f"0x{off:08X} (hex). Open the file in hex-editor and go to that offset."
                        )
                        self.meta_text.insert("end", instr)
                        self.set_status(f"PNG analysis: corrupt chunk '{name}' at offset {off}")
                    else:
                        self.set_status("Opened PNG and analyzed chunks")
                self.root.after(0, ui_update)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to open/analyze PNG: {e}"))
            finally:
                self.root.after(0, pd.close)
        threading.Thread(target=worker, daemon=True).start()

    def save_as_txt(self):
        if not self.current_image_path:
            messagebox.showinfo("Info", "Open an image first.")
            return
        dest = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files","*.txt")])
        if not dest:
            return
        bak = safe_copy_backup(self.current_image_path)
        def worker():
            pd = ProgressDialog(self.root, title="Saving TXT", message=f"Saving {os.path.basename(dest)}")
            try:
                data, w, h = encode_image_lossy_to_text(self.current_image_path)
                with open(dest, "wb") as f:
                    f.write(data)
                self.root.after(0, lambda: messagebox.showinfo("Saved", f"Saved lossy text to {dest}\nBackup: {bak if bak else 'not created'}"))
                self.root.after(0, lambda: self.set_status(f"Saved TXT: {dest}"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to save TXT: {e}"))
            finally:
                self.root.after(0, pd.close)
        threading.Thread(target=worker, daemon=True).start()

    def save_as_fj4(self, lossy: bool):
        if not self.current_image_path:
            messagebox.showinfo("Info", "Open an image first.")
            return
        dest = filedialog.asksaveasfilename(defaultextension=".fj4", filetypes=[("FJ4 container","*.fj4")])
        if not dest:
            return
        if self.alg_var.get() == "lz4" and lz4frame is None:
            messagebox.showerror("Missing", "lz4.frame not installed. pip install lz4")
            return
        if self.alg_var.get() == "zstd" and zstd is None:
            messagebox.showerror("Missing", "zstandard not installed. pip install zstandard")
            return
        bak = safe_copy_backup(self.current_image_path)

        def worker():
            pd = ProgressDialog(self.root, title="Saving .fj4", message=f"Saving {os.path.basename(dest)}")
            try:
                # prepare payload
                if lossy:
                    payload, w, h = encode_image_lossy_to_text(self.current_image_path)
                    mode_lossy = True
                else:
                    with open(self.current_image_path, "rb") as f:
                        payload = f.read()
                    mode_lossy = False

                algo = self.alg_var.get()
                level = int(self.level_var.get())
                tape_mode = bool(self.tape_var.get())
                block_kb = int(self.blocksize_var.get())
                block_size = block_kb * 1024
                parity = 1 if self.parity_var.get() else 0

                # ask for optional password (leave empty for no encryption)
                passwd = self.root.after(0, lambda: None)  # noop to ensure UI thread alive
                # use simpledialog in the main thread (blocking)
                try:
                    passwd = simpledialog.askstring("Encrypt metadata", "Enter password to encrypt metadata (leave empty = no encryption):", show="*", parent=self.root)
                except Exception:
                    passwd = None

                if tape_mode:
                    combined, tape_meta = create_tape_payload(payload, algo, level, block_size, parity)
                    container_meta = {
                        **(self.loaded_metadata or {}),
                        **tape_meta
                    }
                    container_meta["_tape_container"] = True
                    container_meta["_mode_lossy"] = bool(mode_lossy)
                    # remove sensitive fields from metadata
                    container_meta.pop("path", None)
                    container_meta.pop("file_name", None)
                    # optionally encrypt metadata
                    if passwd:
                        try:
                            enc_meta = encrypt_meta_dict(container_meta, passwd)
                        except Exception as e:
                            raise RuntimeError(f"Failed to encrypt metadata: {e}")
                        container = pack_container(combined, compressed=True, mode_lossy=mode_lossy, metadata=enc_meta)
                    else:
                        container = pack_container(combined, compressed=True, mode_lossy=mode_lossy, metadata=container_meta)
                else:
                    # compress whole payload with chosen algo
                    if algo == "lz4":
                        comp_payload = compress_block_lz4(payload)
                    else:
                        comp_payload = compress_block_zstd(payload, level=level)

                    container_meta = {
                        **(self.loaded_metadata or {}),
                        "compression_algo": algo,
                        "compression_level": level,
                        "_mode_lossy": bool(mode_lossy)
                    }
                    # remove sensitive fields from metadata
                    container_meta.pop("path", None)
                    container_meta.pop("file_name", None)
                    # optionally encrypt metadata
                    if passwd:
                        try:
                            enc_meta = encrypt_meta_dict(container_meta, passwd)
                        except Exception as e:
                            raise RuntimeError(f"Failed to encrypt metadata: {e}")
                        container = pack_container(comp_payload, compressed=True, mode_lossy=mode_lossy, metadata=enc_meta)
                    else:
                        container = pack_container(comp_payload, compressed=True, mode_lossy=mode_lossy, metadata=container_meta)

                with open(dest, "wb") as f:
                    f.write(container)

                self.root.after(0, lambda: messagebox.showinfo("Saved", f"Saved container to {dest}\nBackup: {bak if bak else 'not created'}"))
                self.root.after(0, lambda: self.set_status(f"Saved FJ4: {dest}"))
            except Exception as e:
                # show user-friendly error (including encryption failures)
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to save .fj4: {e}"))
            finally:
                self.root.after(0, pd.close)

        threading.Thread(target=worker, daemon=True).start()

    def import_metadata_json(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json"), ("All files","*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            self.loaded_metadata = meta
            self._write_meta_text(self.loaded_metadata)
            messagebox.showinfo("Imported", f"Imported metadata from {path}")
            self.set_status("Imported metadata")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import metadata: {e}")

    def export_metadata_json(self):
        try:
            text = self.meta_text.get("1.0", "end").strip()
            if text:
                obj = json.loads(text)
            else:
                obj = self.loaded_metadata or {}
        except Exception:
            obj = self.loaded_metadata or {}
        dest = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files","*.json")])
        if not dest:
            return
        try:
            with open(dest, "w", encoding="utf-8") as f:
                json.dump(obj, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Saved", f"Metadata exported to {dest}")
            self.set_status(f"Exported metadata to {dest}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export metadata: {e}")

    def save_metadata_into_container(self):
        container_path = self.current_container_path
        if not container_path:
            container_path = filedialog.askopenfilename(filetypes=[("FJ4 files", "*.fj4"), ("All files","*.*")])
            if not container_path:
                return
        try:
            with open(container_path, "rb") as f:
                raw = f.read()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read container: {e}")
            return
        try:
            parsed = unpack_container(raw)
        except Exception as e:
            messagebox.showerror("Error", f"Not a valid container: {e}")
            return
        try:
            new_meta_text = self.meta_text.get("1.0", "end").strip()
            if not new_meta_text:
                new_meta = parsed.get("meta", {})
            else:
                new_meta = json.loads(new_meta_text)
        except Exception as e:
            messagebox.showerror("Error", f"Metadata is not valid JSON: {e}")
            return
        payload = parsed["payload"]
        compressed = parsed["compressed"]
        mode_lossy = parsed["mode_lossy"]
        bak = safe_copy_backup(container_path)
        def worker():
            pd = ProgressDialog(self.root, title="Updating metadata", message=f"Updating metadata in {os.path.basename(container_path)}")
            try:
                new_container = pack_container(payload, compressed=compressed, mode_lossy=mode_lossy, metadata=new_meta)
                with open(container_path, "wb") as f:
                    f.write(new_container)
                self.root.after(0, lambda: messagebox.showinfo("Saved", f"Updated metadata saved into {container_path}\nBackup: {bak if bak else 'not created'}"))
                self.root.after(0, lambda: self.set_status(f"Updated metadata in {container_path}"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to update container metadata: {e}"))
            finally:
                self.root.after(0, pd.close)
        threading.Thread(target=worker, daemon=True).start()

    def open_container(self):
        path = filedialog.askopenfilename(filetypes=[("FJ4 / TXT files", "*.fj4;*.txt"), ("All files","*.*")])
        if not path:
            return
        self.current_container_path = path
        def worker():
            pd = ProgressDialog(self.root, title="Opening", message=f"Opening {os.path.basename(path)}")
            try:
                with open(path, "rb") as f:
                    raw = f.read()
                if raw[:4] == MAGIC:
                    parsed = unpack_container(raw)
                    meta = parsed.get("meta", {})
                    self.loaded_metadata = meta
                    self.root.after(0, lambda: self._write_meta_text(self.loaded_metadata))
                    # If tape_mode in meta, handle special recovery
                    if meta.get("tape_mode"):
                        # combined payload contains padded compressed blocks + parity blocks
                        combined = parsed["payload"]
                        ok, recovered_payload, diag = recover_tape_payload_from_combined(combined, meta)
                        if not ok:
                            self.loaded_metadata["_tape_recovery_diag"] = diag
                            self.root.after(0, lambda: self._write_meta_text(self.loaded_metadata))
                            self.root.after(0, lambda: messagebox.showwarning("Partial", f"Tape recovery failed or partial: {diag}"))
                        else:
                            # recovered_payload is original (pre-block) payload; then process depending on mode_lossy
                            if parsed["mode_lossy"]:
                                try:
                                    img = reconstruct_image_from_text_bytes(recovered_payload)
                                    self.current_image = img
                                    self.root.after(0, lambda: self.display_image(img))
                                except Exception as e:
                                    self.loaded_metadata["_reconstruct_error"] = str(e)
                                    self.root.after(0, lambda: self._write_meta_text(self.loaded_metadata))
                            else:
                                try:
                                    img = Image.open(io.BytesIO(recovered_payload))
                                    self.current_image = img
                                    self.root.after(0, lambda: self.display_image(img))
                                    corrupt_chunk = find_corrupt_png_chunk(recovered_payload)
                                    if corrupt_chunk:
                                        self.loaded_metadata["_png_corrupt_chunk"] = corrupt_chunk
                                except Exception as e:
                                    self.loaded_metadata["_png_open_error"] = str(e)
                                    self.root.after(0, lambda: self._write_meta_text(self.loaded_metadata))
                            self.loaded_metadata["_tape_recovery_diag"] = diag
                            self.root.after(0, lambda: self._write_meta_text(self.loaded_metadata))
                            self.root.after(0, lambda: self.set_status(f"Opened tape-mode container {os.path.basename(path)}"))
                    else:
                        # Non-tape-mode: decompress full payload with chosen algo
                        algo = meta.get("compression_algo", None)
                        if parsed["compressed"]:
                            try:
                                if algo == "zstd" and zstd is not None:
                                    decompressed = decompress_block_zstd(parsed["payload"])
                                else:
                                    # default to lz4 if available
                                    decompressed = decompress_block_lz4(parsed["payload"])
                                sha_ok = sha256_hex(decompressed) == parsed["sha256"].hex()
                                self.loaded_metadata["_sha_ok"] = sha_ok
                                self.loaded_metadata["_sha_stored"] = parsed["sha256"].hex()
                                if parsed["mode_lossy"]:
                                    img = reconstruct_image_from_text_bytes(decompressed)
                                    self.current_image = img
                                    self.root.after(0, lambda: self.display_image(img))
                                else:
                                    img = Image.open(io.BytesIO(decompressed))
                                    self.current_image = img
                                    self.root.after(0, lambda: self.display_image(img))
                                    corrupt_chunk = find_corrupt_png_chunk(decompressed)
                                    self.loaded_metadata["_png_corrupt_chunk"] = corrupt_chunk
                                self.root.after(0, lambda: self._write_meta_text(self.loaded_metadata))
                                self.root.after(0, lambda: self.set_status(f"Opened container {os.path.basename(path)}"))
                            except Exception as e:
                                # decompression failed
                                self.loaded_metadata["_decompress_error"] = str(e)
                                # attempt heuristics
                                off = find_first_corrupt_offset_in_lz4_frame(parsed["payload"]) if lz4frame is not None else None
                                self.loaded_metadata["_approx_corrupt_offset_in_payload"] = off
                                self.root.after(0, lambda: self._write_meta_text(self.loaded_metadata))
                                self.root.after(0, lambda: messagebox.showwarning("Decompress", f"Decompress failed: {e}\nApprox offset: {off}"))
                        else:
                            # not compressed - could be raw txt or png
                            payload = parsed["payload"]
                            if parsed["mode_lossy"]:
                                try:
                                    img = reconstruct_image_from_text_bytes(payload)
                                    self.current_image = img
                                    self.root.after(0, lambda: self.display_image(img))
                                except Exception as e:
                                    self.loaded_metadata["_reconstruct_error"] = str(e)
                                    self.root.after(0, lambda: self._write_meta_text(self.loaded_metadata))
                            else:
                                try:
                                    img = Image.open(io.BytesIO(payload))
                                    self.current_image = img
                                    self.root.after(0, lambda: self.display_image(img))
                                    corrupt_chunk = find_corrupt_png_chunk(payload)
                                    self.loaded_metadata["_png_corrupt_chunk"] = corrupt_chunk
                                    self.root.after(0, lambda: self._write_meta_text(self.loaded_metadata))
                                except Exception as e:
                                    self.loaded_metadata["_open_error"] = str(e)
                                    self.root.after(0, lambda: self._write_meta_text(self.loaded_metadata))
                else:
                    # raw file - try as TXT then PNG
                    try:
                        img = reconstruct_image_from_text_bytes(raw)
                        self.current_image = img
                        self.root.after(0, lambda: self.display_image(img))
                        self.loaded_metadata = {"recovered_from": path, "mode": "plain_txt_recovery"}
                        self.root.after(0, lambda: self._write_meta_text(self.loaded_metadata))
                        self.root.after(0, lambda: self.set_status("Recovered image from plain TXT"))
                    except Exception:
                        try:
                            img = Image.open(io.BytesIO(raw))
                            self.current_image = img
                            self.root.after(0, lambda: self.display_image(img))
                            try:
                                corrupt_chunk = find_corrupt_png_chunk(raw)
                            except Exception:
                                corrupt_chunk = None
                            self.loaded_metadata = {"recovered_from": path, "png_corrupt_chunk": corrupt_chunk}
                            self.root.after(0, lambda: self._write_meta_text(self.loaded_metadata))
                            self.root.after(0, lambda: self.set_status("Opened raw PNG bytes"))
                        except Exception as e:
                            self.root.after(0, lambda: messagebox.showerror("Error", f"File not recognized and salvage failed: {e}"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to open container: {e}"))
            finally:
                self.root.after(0, pd.close)
        threading.Thread(target=worker, daemon=True).start()

# ------------------------------
# Run app
# ------------------------------
def main():
    root = tk.Tk()
    app = App(root)
    root.geometry("1280x800")
    root.mainloop()

if __name__ == "__main__":
    main()
