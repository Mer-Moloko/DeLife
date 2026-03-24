#!/usr/bin/env python3
# resilient_png_tool_v3.py
"""
Resilient PNG tool v3
- GUI (Tkinter) to open PNG, save lossy TXT, save .fj4 container (LZ4-compressed)
- Automatic .bak backup before saving
- Metadata export/import to JSON and editable metadata field
- Save metadata into existing container (updates meta JSON inside .fj4)
- Container format includes metadata JSON and SHA256(payload)
- PNG chunk parsing to detect corrupted chunks (CRC mismatch / truncated) with exact byte offsets
- Progress dialog and background threads for long operations
- Best-effort salvage for lossy text inside raw bytes
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

# Optional lz4 dependency
try:
    import lz4.frame as lz4frame
except Exception:
    lz4frame = None

MAGIC = b"FJ4\x00"
VERSION = 1
HEX_PAIR_RE = re.compile(rb"[0-9A-Fa-f]{2}")

# ------------------------------
# Helper utilities
# ------------------------------
def sha256_bytes(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()

def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def md5_hex(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()

def safe_copy_backup(path: str) -> Optional[str]:
    """
    Create a .bak copy next to the original, unless it already exists.
    Returns backup path or None on failure.
    """
    if not os.path.exists(path):
        return None
    bak_path = path + ".bak"
    try:
        if not os.path.exists(bak_path):
            shutil.copy2(path, bak_path)
        return bak_path
    except Exception:
        return None

# ------------------------------
# Image encode/decode functions
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
# Container pack/unpack with metadata JSON
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
# Compression helpers
# ------------------------------
def compress_lz4(data: bytes) -> bytes:
    if lz4frame is None:
        raise RuntimeError("lz4.frame not available. Install python-lz4: pip install lz4")
    return lz4frame.compress(data)

def decompress_lz4(data: bytes) -> bytes:
    if lz4frame is None:
        raise RuntimeError("lz4.frame not available. Install python-lz4: pip install lz4")
    return lz4frame.decompress(data)

# ------------------------------
# Salvage textual rows (best-effort)
# ------------------------------
def salvage_textual_rows(raw_bytes: bytes):
    try:
        text = raw_bytes.decode("ascii", errors="ignore")
    except:
        text = ""
    lines = text.splitlines()
    width = height = None
    start = 0
    for i, ln in enumerate(lines[:20]):
        parts = ln.strip().split()
        if len(parts) >= 2 and all(p.isdigit() for p in parts[:2]):
            width, height = int(parts[0]), int(parts[1])
            start = i + 1
            break
    if width is None or height is None:
        return None
    rows = []
    for ln in lines[start:start + height]:
        hex_bytes = HEX_PAIR_RE.findall(ln.encode("ascii", errors="ignore"))
        row = bytes(int(h,16) for h in hex_bytes)
        rows.append(row)
    return width, height, rows

# ------------------------------
# PNG chunk analysis with precise byte offsets
# ------------------------------
def analyze_png_bytes(data: bytes) -> List[dict]:
    """
    Parse PNG by chunks and check CRC for each chunk.
    Returns list of chunk dicts: {name, chunk_offset, length, crc_expected, crc_actual, crc_ok, chunk_end_offset, truncated}
    chunk_offset = byte index where the chunk length field starts (i.e. start of this chunk)
    """
    sig = b"\x89PNG\r\n\x1a\n"
    chunks = []
    if len(data) < len(sig) or data[:8] != sig:
        raise ValueError("Not a valid PNG signature")
    idx = 8
    while True:
        if idx + 8 > len(data):
            break
        chunk_offset = idx  # start of length field
        length = struct.unpack(">I", data[idx:idx+4])[0]
        idx += 4
        ctype = data[idx:idx+4]; idx += 4
        # check if enough bytes for data + crc
        if idx + length + 4 > len(data):
            # truncated chunk
            available = len(data) - idx
            chunk_data = data[idx: idx + max(0, available)]
            chunks.append({
                "name": ctype.decode("ascii", errors="ignore"),
                "chunk_offset": chunk_offset,
                "length": length,
                "available_bytes": available,
                "crc_expected": None,
                "crc_actual": None,
                "crc_ok": False,
                "truncated": True,
                "chunk_end_offset": len(data) - 1
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
# Heuristic: find first failing offset inside an LZ4 frame (best-effort)
# ------------------------------
def find_first_corrupt_offset_in_lz4_frame(frame_bytes: bytes) -> Optional[int]:
    if lz4frame is None:
        return None
    # Quick check: full decompression success => no corruption
    try:
        _ = lz4frame.decompress(frame_bytes)
        return None
    except Exception:
        pass
    # attempt to find any prefix that decompresses (unlikely). Try progressive sizes
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
# Progress dialog helper (uses indeterminate mode)
# ------------------------------
class ProgressDialog:
    def __init__(self, parent, title="Working...", message="Please wait"):
        self.top = tk.Toplevel(parent)
        self.top.title(title)
        self.top.resizable(False, False)
        self.top.transient(parent)
        self.top.grab_set()
        ttk.Label(self.top, text=message).pack(padx=10, pady=(10, 4))
        self.pb = ttk.Progressbar(self.top, mode="indeterminate", length=300)
        self.pb.pack(padx=10, pady=(4, 10))
        self.pb.start(20)
        # center on parent
        parent.update_idletasks()
        w = parent.winfo_width(); h = parent.winfo_height()
        x = parent.winfo_rootx() + (w // 2) - 180
        y = parent.winfo_rooty() + (h // 2) - 40
        try:
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
# GUI Application
# ------------------------------
class App:
    def __init__(self, root):
        self.root = root
        root.title("Resilient PNG Encoder v3")
        self.current_image: Optional[Image.Image] = None
        self.current_image_path: Optional[str] = None
        self.loaded_metadata: dict = {}
        self.current_container_path: Optional[str] = None
        self._build_ui()

    def _build_ui(self):
        # Menu
        menubar = tk.Menu(self.root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open PNG...", command=self.open_image)
        filemenu.add_command(label="Open .fj4 / TXT...", command=self.open_container)
        filemenu.add_separator()
        filemenu.add_command(label="Save as TXT (lossy)", command=self.save_as_txt)
        filemenu.add_command(label="Save as .fj4 (lossy, LZ4)", command=lambda: self.save_as_fj4(lossy=True))
        filemenu.add_command(label="Save as .fj4 (lossless, LZ4)", command=lambda: self.save_as_fj4(lossy=False))
        filemenu.add_separator()
        filemenu.add_command(label="Export metadata JSON...", command=self.export_metadata_json)
        filemenu.add_command(label="Import metadata JSON...", command=self.import_metadata_json)
        filemenu.add_separator()
        filemenu.add_command(label="Save metadata into container", command=self.save_metadata_into_container)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=filemenu)
        self.root.config(menu=menubar)

        # Layout frames
        main = ttk.Frame(self.root)
        main.pack(fill="both", expand=True)

        left = ttk.Frame(main, width=360)
        left.pack(side="left", fill="y")

        right = ttk.Frame(main)
        right.pack(side="right", fill="both", expand=True)

        # Metadata panel on left
        meta_label = ttk.Label(left, text="Metadata (editable)", font=("TkDefaultFont", 12, "bold"))
        meta_label.pack(anchor="nw", padx=6, pady=(6, 0))

        self.meta_text = tk.Text(left, width=48, height=20)
        self.meta_text.pack(padx=6, pady=6, expand=False)
        # Buttons under metadata
        meta_btns = ttk.Frame(left)
        meta_btns.pack(fill="x", padx=6, pady=(0,6))
        ttk.Button(meta_btns, text="Import JSON", command=self.import_metadata_json).pack(side="left", expand=True, fill="x")
        ttk.Button(meta_btns, text="Export JSON", command=self.export_metadata_json).pack(side="left", expand=True, fill="x")
        ttk.Button(meta_btns, text="Save metadata into container", command=self.save_metadata_into_container).pack(side="left", expand=True, fill="x")

        # Canvas with scrollbars on right
        self.canvas_frame = ttk.Frame(right)
        self.canvas_frame.pack(fill="both", expand=True)

        self.vbar = ttk.Scrollbar(self.canvas_frame, orient="vertical")
        self.hbar = ttk.Scrollbar(self.canvas_frame, orient="horizontal")
        self.canvas = tk.Canvas(self.canvas_frame, bd=0, highlightthickness=0,
                                xscrollcommand=self.hbar.set, yscrollcommand=self.vbar.set, background="#222")
        self.hbar.config(command=self.canvas.xview)
        self.vbar.config(command=self.canvas.yview)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vbar.grid(row=0, column=1, sticky="ns")
        self.hbar.grid(row=1, column=0, sticky="ew")
        self.canvas_frame.rowconfigure(0, weight=1)
        self.canvas_frame.columnconfigure(0, weight=1)

        # status bar
        self.status = tk.StringVar(value="Ready")
        statusbar = ttk.Label(self.root, textvariable=self.status, relief="sunken", anchor="w")
        statusbar.pack(fill="x", side="bottom")

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
        # write pretty JSON to meta_text and keep it editable
        try:
            pretty = json.dumps(meta_obj, ensure_ascii=False, indent=2)
        except Exception:
            pretty = str(meta_obj)
        self.meta_text.delete("1.0", "end")
        self.meta_text.insert("1.0", pretty)

    # ------------------------------
    # File operations (use threads for heavy ops)
    # ------------------------------
    def open_image(self):
        path = filedialog.askopenfilename(filetypes=[("PNG files", "*.png"), ("All files", "*.*")])
        if not path:
            return
        # run reading + analysis in worker thread
        def worker():
            pd = ProgressDialog(self.root, title="Opening...", message=f"Opening {os.path.basename(path)}")
            try:
                with open(path, "rb") as f:
                    data = f.read()
                img = Image.open(io.BytesIO(data))
                # analyze png chunks
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
                # push to UI thread
                def ui_update():
                    self.current_image = img.copy()
                    self.current_image_path = path
                    self.current_container_path = None
                    self.display_image(self.current_image)
                    self.loaded_metadata = meta
                    self._write_meta_text(self.loaded_metadata)
                    if corrupt_chunk:
                        # create instruction to open in hex editor
                        off = corrupt_chunk.get("chunk_offset")
                        name = corrupt_chunk.get("name")
                        instr = (
                            f"\n\nInstruction: Corrupted chunk '{name}' at byte offset {off} (decimal), "
                            f"0x{off:08X} (hex).\n"
                            f"Open the file in a hex editor and go to that offset. The chunk header begins at that offset\n"
                            f"(4 bytes length, then 4 bytes type '{name}'). You can compare CRC expected vs actual "
                            f"from metadata (crc_expected / crc_actual) and attempt to locate a valid replacement "
                            f"from a backup or re-download the file.\n"
                        )
                        # append to meta display
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
        # create .bak
        bak = safe_copy_backup(self.current_image_path)
        def worker():
            pd = ProgressDialog(self.root, title="Saving TXT", message=f"Saving to {os.path.basename(dest)}")
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
        if lz4frame is None:
            messagebox.showerror("Missing dependency", "lz4.frame not found. Install with: pip install lz4")
            return
        dest = filedialog.asksaveasfilename(defaultextension=".fj4", filetypes=[("FJ4 container","*.fj4")])
        if not dest:
            return
        bak = safe_copy_backup(self.current_image_path)
        def worker():
            pd = ProgressDialog(self.root, title="Saving .fj4", message=f"Compressing and saving {os.path.basename(dest)}")
            try:
                if lossy:
                    payload, w, h = encode_image_lossy_to_text(self.current_image_path)
                    mode_lossy = True
                else:
                    with open(self.current_image_path, "rb") as f:
                        payload = f.read()
                    mode_lossy = False
                compressed_payload = compress_lz4(payload)
                meta = dict(self.loaded_metadata or {})
                meta.update({
                    "_saved_by": "resilient_png_tool_v3",
                    "_original_path": self.current_image_path,
                    "_mode_lossy": bool(mode_lossy),
                    "_created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                })
                container = pack_container(compressed_payload, compressed=True, mode_lossy=mode_lossy, metadata=meta)
                with open(dest, "wb") as f:
                    f.write(container)
                self.root.after(0, lambda: messagebox.showinfo("Saved", f"Saved container to {dest}\nBackup: {bak if bak else 'not created'}"))
                self.root.after(0, lambda: self.set_status(f"Saved FJ4: {dest}"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to save .fj4: {e}"))
            finally:
                self.root.after(0, pd.close)
        threading.Thread(target=worker, daemon=True).start()

    def export_metadata_json(self):
        # read meta_text (attempt to parse JSON if possible)
        try:
            text = self.meta_text.get("1.0", "end").strip()
            if not text:
                messagebox.showinfo("Info", "No metadata to export")
                return
            obj = json.loads(text)
        except Exception:
            # fallback to using loaded_metadata
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

    def import_metadata_json(self):
        path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json"), ("All files","*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            self.loaded_metadata = meta
            self._write_meta_text(self.loaded_metadata)
            messagebox.showinfo("Imported", f"Imported metadata from {path}")
            self.set_status(f"Imported metadata")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import metadata: {e}")

    def save_metadata_into_container(self):
        """
        Update meta JSON inside an existing container file (self.current_container_path).
        Creates .bak copy first.
        """
        # Determine container path
        container_path = self.current_container_path
        if not container_path:
            # prompt user to select container to update
            container_path = filedialog.askopenfilename(filetypes=[("FJ4 files", "*.fj4"), ("All files", "*.*")])
            if not container_path:
                return
        # Read existing container and replace metadata
        try:
            with open(container_path, "rb") as f:
                raw = f.read()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read container: {e}")
            return
        # Parse header to know where payload starts
        try:
            parsed = unpack_container(raw)
        except Exception as e:
            messagebox.showerror("Error", f"Not a valid container: {e}")
            return
        # Read edited metadata from meta_text
        try:
            new_meta_text = self.meta_text.get("1.0", "end").strip()
            if not new_meta_text:
                new_meta = parsed.get("meta", {})
            else:
                new_meta = json.loads(new_meta_text)
        except Exception as e:
            messagebox.showerror("Error", f"Metadata is not valid JSON: {e}")
            return
        # Build new container with same payload (keep compressed payload as-is)
        payload = parsed["payload"]
        compressed = parsed["compressed"]
        mode_lossy = parsed["mode_lossy"]
        # backup
        bak = safe_copy_backup(container_path)
        def worker():
            pd = ProgressDialog(self.root, title="Updating metadata", message=f"Updating metadata in {os.path.basename(container_path)}")
            try:
                # new container
                # payload is already compressed if parsed['compressed'] == True; we keep it unchanged.
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
            pd = ProgressDialog(self.root, title="Opening container", message=f"Opening {os.path.basename(path)}")
            try:
                with open(path, "rb") as f:
                    raw = f.read()
                if raw[:4] == MAGIC:
                    parsed = unpack_container(raw)
                    meta = parsed.get("meta", {})
                    self.loaded_metadata = meta
                    # show meta in text (editable)
                    def ui_meta():
                        self._write_meta_text(self.loaded_metadata)
                    self.root.after(0, ui_meta)
                    # try to decompress payload (in background)
                    if parsed["compressed"]:
                        try:
                            decompressed = decompress_lz4(parsed["payload"])
                            sha_ok = sha256_hex(decompressed) == parsed["sha256"].hex()
                            if parsed["mode_lossy"]:
                                img = reconstruct_image_from_text_bytes(decompressed)
                                self.current_image = img
                                self.root.after(0, lambda: self.display_image(img))
                            else:
                                # open PNG -> analyze chunks
                                try:
                                    img = Image.open(io.BytesIO(decompressed))
                                    self.current_image = img
                                    self.root.after(0, lambda: self.display_image(img))
                                    # analyze png
                                    corrupt_chunk = find_corrupt_png_chunk(decompressed)
                                except Exception as ex:
                                    corrupt_chunk = find_corrupt_png_chunk(decompressed) if isinstance(ex, Exception) else None
                                # update metadata with sha and png analysis
                                meta_update = dict(meta or {})
                                meta_update["_sha_ok"] = sha_ok
                                meta_update["_sha_stored"] = parsed["sha256"].hex()
                                meta_update["_approx_png_corrupt_chunk"] = corrupt_chunk
                                self.loaded_metadata = meta_update
                                self.root.after(0, lambda: self._write_meta_text(self.loaded_metadata))
                        except Exception as e:
                            # decompression failed -> attempt to locate corrupt offset in payload
                            off = find_first_corrupt_offset_in_lz4_frame(parsed["payload"])
                            meta_update = dict(meta or {})
                            meta_update["_decompress_error"] = str(e)
                            meta_update["_approx_corrupt_offset_in_lz4_payload"] = off
                            # if mode_lossy try salvage from raw
                            if parsed["mode_lossy"]:
                                salv = salvage_textual_rows(raw)
                                if salv:
                                    w,h,rows = salv
                                    img = Image.new("L",(w,h))
                                    for y,row in enumerate(rows):
                                        for x,val in enumerate(row[:w]):
                                            img.putpixel((x,y), val)
                                    self.current_image = img
                                    self.root.after(0, lambda: self.display_image(img))
                                    meta_update["_salvage_rows"] = len(rows)
                                else:
                                    meta_update["_salvage"] = "failed"
                            self.loaded_metadata = meta_update
                            self.root.after(0, lambda: self._write_meta_text(self.loaded_metadata))
                    else:
                        # not compressed - payload may be raw txt or raw png bytes
                        payload = parsed["payload"]
                        sha_ok = sha256_hex(payload) == parsed["sha256"].hex()
                        meta_update = dict(meta or {})
                        meta_update["_sha_ok"] = sha_ok
                        meta_update["_sha_stored"] = parsed["sha256"].hex()
                        if parsed["mode_lossy"]:
                            try:
                                img = reconstruct_image_from_text_bytes(payload)
                                self.current_image = img
                                self.root.after(0, lambda: self.display_image(img))
                            except Exception as e:
                                meta_update["_reconstruct_error"] = str(e)
                        else:
                            try:
                                img = Image.open(io.BytesIO(payload))
                                self.current_image = img
                                self.root.after(0, lambda: self.display_image(img))
                                corrupt_chunk = find_corrupt_png_chunk(payload)
                                meta_update["_png_corrupt_chunk"] = corrupt_chunk
                            except Exception as e:
                                meta_update["_png_open_error"] = str(e)
                        self.loaded_metadata = meta_update
                        self.root.after(0, lambda: self._write_meta_text(self.loaded_metadata))
                    self.root.after(0, lambda: self.set_status(f"Opened container {os.path.basename(path)}"))
                else:
                    # not container; try to interpret as plain txt or png bytes
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
                            self.root.after(0, lambda: messagebox.showerror("Error", f"Unrecognized file and salvage failed: {e}"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to open container: {e}"))
            finally:
                self.root.after(0, pd.close)
        threading.Thread(target=worker, daemon=True).start()

# ------------------------------
# Run
# ------------------------------
def main():
    root = tk.Tk()
    app = App(root)
    root.geometry("1200x760")
    root.mainloop()

if __name__ == "__main__":
    main()
