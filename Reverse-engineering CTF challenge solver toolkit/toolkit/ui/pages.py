"""The individual solver/analysis pages shown in the main window."""

from __future__ import annotations

import customtkinter as ctk

from ..core import (ciphers, encodings, entropy, fileinfo, frequency,
                    hexdump, strings)
from .widgets import MONO, ResultBox, Toolbar, Worker, ghost_button, primary_button


class ToolPage(ctk.CTkFrame):
    """Base class: a page that can read the app's loaded payload."""

    def __init__(self, master, app, title: str, subtitle: str = ""):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        self.tb = Toolbar(self, title, subtitle)
        self.tb.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.hint = ctk.CTkLabel(self, text="", text_color="#8b93a5",
                                 font=ctk.CTkFont(size=12), anchor="w", justify="left")
        self.hint.grid(row=2, column=0, sticky="ew", pady=(4, 6))

    def body(self):
        raise NotImplementedError

    def output(self, rows: int = 1) -> ResultBox:
        box = ResultBox(self, height=1)
        box.grid(row=3, column=0, sticky="nsew", pady=(6, 0))
        self.grid_rowconfigure(3, weight=1)
        return box

    def payload_bytes(self, max_bytes: int | None = None) -> bytes:
        """Return current input (typed text or loaded file) as bytes."""
        data = self.app.current_bytes
        if data is None:
            return b""
        if max_bytes and len(data) > max_bytes:
            return data[:max_bytes]
        return data

    def guard(self) -> bool:
        if self.app.current_bytes:
            return True
        self.hint.configure(text="Load a file first (Open File in the sidebar).")
        return False


class HomePage(ToolPage):
    def __init__(self, master, app):
        super().__init__(master, app, "Welcome",
                         "Reverse-engineering triage + classic crypto solvers in one toolkit")
        self.grid_rowconfigure(1, weight=1)
        hero = ctk.CTkFrame(self, fg_color="#0f1420", corner_radius=14,
                            border_color="#263048", border_width=1)
        hero.grid(row=1, column=0, sticky="ew", pady=8)
        ctk.CTkLabel(hero, text="RE CTF Challenge Solver Toolkit",
                     font=ctk.CTkFont(size=26, weight="bold"),
                     text_color="#e7ebf3").pack(pady=(24, 4))
        ctk.CTkLabel(hero, text="Load a binary, then run strings, entropy, hex, frequency and crypto solvers.\n"
                                "Every tool can be exported to a polished HTML report.",
                     text_color="#8b93a5", justify="center").pack(pady=(4, 20))
        row = ctk.CTkFrame(hero, fg_color="transparent")
        row.pack(pady=(0, 24))
        primary_button(row, "Open File \u2192", app.open_file).pack(side="left", padx=8)
        ghost_button(row, "Generate HTML Report", app.goto_report).pack(side="left", padx=8)

        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.grid(row=3, column=0, sticky="nsew", pady=(16, 0))
        grid.grid_columnconfigure((0, 1), weight=1, uniform="g")
        tips = [
            ("Strings", "Extract ASCII/Unicode strings with offsets - spot flag{} patterns fast."),
            ("Entropy", "Shannon entropy per block spots packed / encrypted payloads."),
            ("Hex Dump", "Inspect magic bytes and raw structure at any offset."),
            ("Encodings", "Hex, Base64/32/58/85, URL, ROT13 + auto-detection."),
            ("Cipher Solvers", "XOR (single/multi-byte), Caesar, Atbash, Vigenere breaking."),
            ("Frequency", "Letter histogram to steer substitution analysis."),
        ]
        for i, (t, d) in enumerate(tips):
            card = ctk.CTkFrame(grid, fg_color="#141925", corner_radius=10,
                                border_color="#263048", border_width=1)
            card.grid(row=i // 2, column=i % 2, sticky="nsew", padx=6, pady=6)
            ctk.CTkLabel(card, text=t, font=ctk.CTkFont(size=15, weight="bold"),
                         text_color="#2dd4bf", anchor="w").pack(anchor="w", padx=14, pady=(12, 2))
            ctk.CTkLabel(card, text=d, text_color="#a7b6d0", anchor="w",
                         justify="left", wraplength=380).pack(anchor="w", padx=14, pady=(0, 12))


class FileInfoPage(ToolPage):
    def __init__(self, master, app):
        super().__init__(master, app, "File Information",
                         "Metadata, hashes, magic bytes and PE/ELF header parsing")
        self.box = self.output()
        self.tb.add_trailing(primary_button(self, "Analyze", self.run), 1)

    def run(self):
        if not self.guard():
            return
        data = self.app.current_bytes
        info = fileinfo.FileInfo(self.app.current_path)
        self.hint.configure(text="")
        self.box.clear()
        self.box.write("Analyzing...", "info")
        Worker(self, lambda: _file_info_work(info, data), self._show)

    def _show(self, result, err):
        if err is not None:
            self.box.clear()
            self.box.write(f"Error: {err}", "bad")
            return
        info, extra = result
        for k, v in info.items():
            self.box.write_pair(k.upper().replace("_", " "), str(v))
        if extra:
            self.box.write("", "")
            for k, v in extra.items():
                self.box.write_pair(k, str(v), "warn")


def _file_info_work(info, data):
    merged = info.info()
    merged["extra"] = fileinfo.deep_header_info(data)
    return merged, merged["extra"]


class StringsPage(ToolPage):
    def __init__(self, master, app):
        super().__init__(master, app, "Strings",
                         "Extract ASCII & UTF-16 strings with file offsets")
        ctl = ctk.CTkFrame(self, fg_color="transparent")
        ctl.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(ctl, text="Min length").pack(side="left", padx=(0, 6))
        self.min_len = ctk.CTkSlider(ctl, from_=2, to=16, number_of_steps=14,
                                     command=self._min_changed)
        self.min_len.set(5)
        self.min_len.pack(side="left", padx=6)
        self.min_lbl = ctk.CTkLabel(ctl, text="5", width=26)
        self.min_lbl.pack(side="left", padx=(6, 16))
        self.uni = ctk.CTkCheckBox(ctl, text="UTF-16", onvalue=1, offvalue=0)
        self.uni.select()
        self.uni.pack(side="left", padx=6)
        self.box = self.output()
        primary_button(ctl, "Extract", self.run).pack(side="right")

    def _min_changed(self, v):
        self.min_lbl.configure(text=str(int(v)))
        self.run()

    def run(self):
        if not self.guard():
            return
        data = self.app.current_bytes
        min_len = int(self.min_len.get())
        self.box.clear()
        self.box.write("Extracting...", "info")
        Worker(self, lambda: strings.extract(data, min_len=min_len,
                                             include_unicode=bool(self.uni.get())),
               self._show)

    def _show(self, result, err):
        if err is not None:
            self.box.write(f"Error: {err}", "bad")
            return
        self.box.clear()
        self.box.write(f"{len(result)} strings found", "ok")
        self.box.write("", "")
        n = len(result)
        for i, s in enumerate(result):
            val = s["value"]
            if len(val) > 300:
                val = val[:300] + "..."
            tag = "ok" if ("flag" in val.lower() or "ctf" in val.lower()) else "text"
            kind = "U" if s["kind"] == "unicode" else "A"
            if n > 2500 and i > 2500:
                self.box.write(f"... {n - 2500} more strings hidden", "dim")
                break
            self.box.write(f"0x{s['offset']:08X} [{kind}] ", "dim", end="")
            self.box.write(val, tag)


class HexPage(ToolPage):
    def __init__(self, master, app):
        super().__init__(master, app, "Hex Dump",
                         "Offset-aware hexadecimal and ASCII dump")
        ctl = ctk.CTkFrame(self, fg_color="transparent")
        ctl.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.box = self.output()
        self.limit = ctk.CTkEntry(ctl, width=90, placeholder_text="rows")
        self.limit.insert(0, "200")
        self.limit.pack(side="left", padx=6)
        primary_button(ctl, "Dump", self.run).pack(side="right")

    def run(self):
        if not self.guard():
            return
        data = self.app.current_bytes
        try:
            rows = max(20, min(int(self.limit.get()), 20000))
        except ValueError:
            rows = 200
        self.box.clear()
        self.box.write("Offset      Hex                                            ASCII", "dim")
        self.box.write("-" * 110, "dim")
        Worker(self, lambda: hexdump.generate(data, 16)[:rows], self._show)

    def _show(self, result, err):
        if err is not None:
            self.box.write(f"Error: {err}", "bad")
            return
        for r in result:
            self.box.write(f"0x{r['offset']:08X}      {r['hex']:<45}  {r['ascii']}", "text", end="\n")


class EntropyPage(ToolPage):
    def __init__(self, master, app):
        super().__init__(master, app, "Entropy Analysis",
                         "Shannon entropy: structure, compression and packing triage")
        ctl = ctk.CTkFrame(self, fg_color="transparent")
        ctl.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.box = self.output()
        primary_button(ctl, "Compute", self.run).pack(side="right")
        self.box.write("Press Compute to analyse the loaded file.", "dim")

    def run(self):
        if not self.guard():
            return
        data = self.app.current_bytes
        self.box.clear()
        self.box.write("Computing...", "info")
        Worker(self, lambda: entropy.file_entropy(data), self._show)

    def _show(self, result, err):
        if err is not None:
            self.box.write(f"Error: {err}", "bad")
            return
        self.box.clear()
        self.box.write_pair("Overall entropy", f"{result['overall']:.4f} bits / byte", "ok")
        self.box.write_pair("Block min / max", f"{result['block_min']:.3f} / {result['block_max']:.3f}")
        self.box.write_pair("Block average", f"{result['block_avg']:.3f}")
        self.box.write_pair("Verdict", result.get("verdict", ""), "warn")
        self.box.write("", "")
        self.box.write("Block entropy band (256-byte blocks):", "dim")
        blocks = result["blocks"]
        if len(blocks) > 128:
            stride = len(blocks) / 128.0
            blocks = [blocks[int(i * stride)] for i in range(128)]
        width = 80
        for eng in blocks:
            filled = int(eng / 8.0 * width)
            bar = "\u2588" * filled + "\u2591" * (width - filled)
            tag = "ok" if eng < 4.5 else ("warn" if eng < 6.5 else "bad")
            self.box.write(f"{eng:6.3f} |{bar}|", tag)


class FrequencyPage(ToolPage):
    def __init__(self, master, app):
        super().__init__(master, app, "Letter Frequency",
                         "Count letters in the loaded bytes to guide substitution work")
        ctl = ctk.CTkFrame(self, fg_color="transparent")
        ctl.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.box = self.output()
        primary_button(ctl, "Analyze", self.run).pack(side="right")

    def run(self):
        if not self.guard():
            return
        data = self.app.current_bytes
        self.box.clear()
        Worker(self, lambda: frequency.letter_histogram(data), self._show)

    def _show(self, result, err):
        if err is not None:
            self.box.write(f"Error: {err}", "bad")
            return
        self.box.clear()
        max_pct = max((f["percent"] for f in result), default=1.0)
        for f in result:
            bar = int(f["percent"] / max_pct * 60)
            self.box.write(
                f" {f['letter']}  {f['percent']:6.2f}%  "
                f"\u2588" * bar + " " * (60 - bar) + f"  {f['count']}", "text"
            )


class EncodePage(ToolPage):
    def __init__(self, master, app):
        super().__init__(master, app, "Encoding Toolbox",
                         "Hex / Base64 / Base32 / Base58 / Base85 / URL / ROT13 / Binary")
        self.grid_rowconfigure(3, weight=1)
        self.grid_rowconfigure(2, weight=0)
        inp = ctk.CTkFrame(self, fg_color="transparent")
        inp.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.input = ctk.CTkEntry(inp, placeholder_text="Paste text (or use loaded file via 'Use File')",
                                  height=32)
        self.input.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ghost_button(inp, "Use File", self.use_file).pack(side="left")

        ctl = ctk.CTkFrame(self, fg_color="transparent")
        ctl.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        self.mode = ctk.CTkSegmentedButton(ctl, values=["Decode", "Encode"], width=180)
        self.mode.set("Decode")
        self.mode.pack(side="left", padx=6)
        self.method = ctk.CTkOptionMenu(ctl, values=list(encodings.ENCODINGS.keys()), width=150)
        self.method.set("Base64")
        self.method.pack(side="left", padx=6)
        ghost_button(ctl, "Auto-detect", self.auto).pack(side="left", padx=6)
        self.box = self.output()
        primary_button(ctl, "Run", self.run).pack(side="right")

    def use_file(self):
        if self.app.current_bytes:
            try:
                self.input.delete(0, "end")
                self.input.insert(0, self.app.current_bytes.decode("utf-8", "ignore")[:4000])
            except Exception:
                pass
        else:
            self.hint.configure(text="Load a file first.")

    def _payload(self) -> bytes | None:
        text = self.input.get().strip()
        if text:
            return text.encode("utf-8")
        if self.payload_bytes():
            return self.payload_bytes()
        self.hint.configure(text="Enter text or load a file.")
        return None

    def run(self):
        data = self._payload()
        if data is None:
            return
        name = self.method.get()
        try:
            self.box.clear()
            if name == "ROT13":
                out = encodings.rot13(data)
            elif self.mode.get() == "Encode":
                enc = encodings.ENCODINGS[name][1]
                out = enc(data)
            else:
                dec = encodings.ENCODINGS[name][2]
                out = dec(data.decode("utf-8", "ignore"))
            self.show_result(name, out)
        except encodings.EncodeError as exc:
            self.box.clear()
            self.box.write(f"Decode failed: {exc}", "bad")
        except Exception as exc:  # noqa: BLE001
            self.box.clear()
            self.box.write(f"Error: {exc}", "bad")

    def show_result(self, name, out):
        self.box.clear()
        if isinstance(out, bytes):
            try:
                text = out.decode("ascii")
                self.box.write_pair(name + " (ASCII-suggested)", text, "ok")
            except UnicodeDecodeError:
                self.box.write_pair(name + " (hex)", out.hex(" ").upper(), "ok")
        else:
            self.box.write_pair(name, str(out), "ok")

    def auto(self):
        data = self._payload()
        if data is None:
            return
        self.box.clear()
        self.box.write("Auto-detection pass:", "info")
        results = encodings.decode_auto(data)
        if not results:
            self.box.write("No encodings decoded cleanly.", "warn")
            return
        for r in results:
            self.box.write(f"[{r['name']}] ", "key", end="")
            self.box.write(r["decoded"], "text")


class XorPage(ToolPage):
    def __init__(self, master, app):
        super().__init__(master, app, "XOR Solver",
                         "Single-byte brute force, multi-byte breaking and known keys")
        ctl = ctk.CTkFrame(self, fg_color="transparent")
        ctl.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.max_len = ctk.CTkEntry(ctl, width=50)
        self.max_len.insert(0, "16")
        self.max_len.pack(side="left", padx=(8, 4))
        ctk.CTkLabel(ctl, text="max key len").pack(side="left", padx=(0, 16))
        self.box = self.output()
        primary_button(ctl, "Single byte", self.single).pack(side="right")
        ghost_button(ctl, "Multi byte", self.multi).pack(side="right", padx=6)
        ghost_button(ctl, "Known keys", self.known).pack(side="right")

    def _guard_max(self) -> int:
        try:
            return max(1, min(int(self.max_len.get()), 48))
        except ValueError:
            return 16

    def single(self):
        if not self.guard():
            return
        data = self.payload_bytes(131072)
        self.box.clear()
        self.box.write("Brute forcing 256 keys...", "info")
        Worker(self, lambda: ciphers.xor_single_byte(data, top=12), lambda r, e: self._show_keyed(r, e))

    def multi(self):
        if not self.guard():
            return
        data = self.payload_bytes(131072)
        self.box.clear()
        self.box.write(f"Breaking multi-byte keys up to length {self._guard_max()}...", "info")
        Worker(self, lambda: ciphers.xor_multi_byte(data, max_key_len=self._guard_max(), top=6),
               lambda r, e: self._show_keyed(r, e, multi=True))

    def known(self):
        if not self.guard():
            return
        data = self.payload_bytes(131072)
        self.box.clear()
        self.box.write("Testing common XOR keys...", "info")
        Worker(self, lambda: ciphers.xor_known_keys(data, top=8), lambda r, e: self._show_keyed(r, e))

    def _show_keyed(self, result, err, multi=False):
        if err is not None:
            self.box.write(f"Error: {err}", "bad")
            return
        self.box.clear()
        for i, r in enumerate(result, 1):
            if multi:
                title = f"# {i}  key len {r['key_len']}  key {r['key_repr']}  ({r['key_hex']})"
            elif "key_name" in r:
                title = f"# {i}  key name '{r['key_name']}'  score {r['score']:.1f}"
            else:
                title = f"# {i}  key 0x{r['key_hex']:0{2}}  score {r['score']:.1f}"
            self.box.write(title, "key")
            self.box.write(preview_str(r["data"]), "text")
            self.box.write("", "")


def preview_str(data, limit=1600) -> str:
    if isinstance(data, bytes):
        try:
            out = data.decode("ascii")
        except UnicodeDecodeError:
            out = data[:96].hex(" ").upper() + "  (binary)"
    else:
        out = str(data)
    return out[:limit] + ("..." if len(out) > limit else "")


class CaesarPage(ToolPage):
    def __init__(self, master, app):
        super().__init__(master, app, "Caesar / Atbash",
                         "Try all 26 rotations on the payload and rank them by English score")
        ctl = ctk.CTkFrame(self, fg_color="transparent")
        ctl.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.box = self.output()
        primary_button(ctl, "Brute force", self.run).pack(side="right")
        ghost_button(ctl, "Atbash", self.atbash).pack(side="right", padx=6)

    def run(self):
        if not self.guard():
            return
        data = self.payload_bytes(65536)
        self.box.clear()
        self.box.write("Trying all shifts...", "info")
        Worker(self, lambda: ciphers.caesar_brute(data, top=26), self._show)

    def _show(self, result, err):
        if err is not None:
            self.box.write(f"Error: {err}", "bad")
            return
        self.box.clear()
        for r in result[:5]:
            self.box.write(f"Shift {r['shift']:>2}  score {r['score']:.2f}", "key")
            self.box.write(preview_str(r["data"]), "text")
            self.box.write("", "")

    def atbash(self):
        if not self.guard():
            return
        data = self.payload_bytes(65536)
        self.box.clear()
        self.box.write("Atbash (a<->z) applied:", "info")
        self.box.write(preview_str(ciphers.atbash(data)), "text")


class VigenerePage(ToolPage):
    def __init__(self, master, app):
        super().__init__(master, app, "Vigenere Solver",
                         "Auto key-length guess + column Caesar, or decode with a known key")
        ctl = ctk.CTkFrame(self, fg_color="transparent")
        ctl.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.key = ctk.CTkEntry(ctl, placeholder_text="known key (optional)", width=220)
        self.key.pack(side="left", padx=6)
        self.box = self.output()
        primary_button(ctl, "Break", self.break_it).pack(side="right")
        ghost_button(ctl, "Use key", self.use_key).pack(side="right", padx=6)

    def break_it(self):
        if not self.guard():
            return
        data = self.payload_bytes(65536)
        self.box.clear()
        self.box.write("Indicative key-length scan + per-column solve...", "info")
        Worker(self, lambda: ciphers.vigenere(data, None), self._show)

    def use_key(self):
        if not self.guard():
            return
        data = self.payload_bytes(65536)
        key = self.key.get().strip()
        if not key:
            self.hint.configure(text="Enter a key, or use Break.")
            return
        self.box.clear()
        Worker(self, lambda: ciphers.vigenere(data, key), self._show)

    def _show(self, result, err):
        if err is not None:
            self.box.write(f"Error: {err}", "bad")
            return
        if "error" in result:
            self.box.write(f"Error: {result['error']}", "bad")
            return
        self.box.clear()
        self.box.write_pair("Method", result.get("method", ""), "key")
        self.box.write_pair("Key", result.get("key", ""), "ok")
        self.box.write_pair("Score", f"{result.get('score', 0):.2f}")
        self.box.write("", "")
        self.box.write(preview_str(result.get("data", b"")), "text")