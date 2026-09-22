"""
app.py -- GLM Beacon Lab console (Tkinter, dark SOC theme).

Three panes: live event feed (left), campaign controls (right), and a
bottom "Decryption Lab" where captured frames are cracked open frame by
frame -- the blue-team payoff.

Educational software. Not for use on systems you do not own.
"""

from __future__ import annotations

import os
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine import beacon as beacon_mod                     # noqa: E402
from engine import decrypt as decrypt_mod                   # noqa: E402
from engine import report as report_mod                     # noqa: E402
from engine.crypto_tools import hexdump                     # noqa: E402
from engine.listener import LabListener, TrafficEvent       # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------

BG = "#0b0f14"
PANEL = "#121821"
PANEL2 = "#0e141c"
LINE = "#1d2633"
TEXT = "#d7e1ee"
MUTED = "#7d8ca1"
ACCENT = "#22d3ee"
ACCENT2 = "#a78bfa"
GOOD = "#34d399"
WARN = "#fbbf24"
BAD = "#f87171"

FONT = ("Segoe UI", 10)
FONT_B = ("Segoe UI", 10, "bold")
FONT_T = ("Segoe UI", 15, "bold")
MONO = ("Consolas", 9)
MONO_S = ("Consolas", 8)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GLM Beacon Lab  ·  Encrypted C2 Channel Demo (TLS-wrapped beacon) + Traffic Decryption for Blue Team Study")
        self.geometry("1360x860")
        self.minsize(1100, 700)
        self.configure(bg=BG)

        # state
        self.listener: LabListener | None = None
        self.beacons: list[beacon_mod.Beacon] = []
        self.event_seq = 0
        self.last_nonce = None
        self.captured_frames: list[bytes] = []
        self._frame_map: dict[str, bytes] = {}

        self._build_style()
        self._build_layout()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(400, self._poll_events)

    # -- style ---------------------------------------------------------------

    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL, foreground=MUTED,
                        padding=(18, 8), font=FONT_B)
        style.map("TNotebook.Tab", background=[("selected", PANEL2)],
                  foreground=[("selected", ACCENT)])
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=TEXT, font=FONT)
        style.configure("Panel.TLabel", background=PANEL, foreground=TEXT, font=FONT)
        style.configure("Muted.TLabel", background=PANEL, foreground=MUTED,
                        font=("Segoe UI", 9))
        style.configure("Title.TLabel", background=BG, foreground=TEXT, font=FONT_T)
        style.configure("Card.TLabel", background=PANEL, foreground=MUTED,
                        font=("Segoe UI", 9))
        style.configure("TButton", background=PANEL, foreground=TEXT,
                        borderwidth=0, padding=8, font=FONT_B)
        style.map("TButton", background=[("active", LINE)])
        style.configure("Accent.TButton", background="#0e7490", foreground="#e0faff")
        style.map("Accent.TButton", background=[("active", "#0891b2")])
        style.configure("TEntry", fieldbackground=PANEL2, foreground=TEXT,
                        insertcolor=TEXT, borderwidth=0, padding=6)
        style.configure("TSpinbox", fieldbackground=PANEL2, foreground=TEXT,
                        borderwidth=0, padding=4, arrowcolor=ACCENT)
        style.configure("TCombobox", fieldbackground=PANEL2, foreground=TEXT,
                        borderwidth=0, arrowcolor=ACCENT)
        style.configure("Vertical.TScrollbar", background=PANEL, troughcolor=BG,
                        bordercolor=BG, arrowcolor=MUTED)

    # -- layout --------------------------------------------------------------

    def _build_layout(self):
        # top bar
        top = tk.Frame(self, bg=BG, pady=14, padx=20)
        top.pack(fill="x")
        logo = tk.Canvas(top, width=42, height=42, bg=BG, highlightthickness=0)
        logo.create_oval(2, 2, 40, 40, fill="#0e7490", outline="")
        logo.create_text(21, 21, text="🛡", font=("Segoe UI Emoji", 17), fill="white")
        logo.pack(side="left")
        titles = tk.Frame(top, bg=BG)
        titles.pack(side="left", padx=12)
        tk.Label(titles, text="GLM BEACON LAB", bg=BG, fg=TEXT,
                 font=("Segoe UI", 15, "bold")).pack(anchor="w")
        tk.Label(titles, text="Encrypted C2 channel demo · TLS-wrapped beacon · blue-team decryption exercise",
                 bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")
        self.status_pill = tk.Label(top, text="● OFFLINE", bg=BG, fg=BAD,
                                    font=FONT_B)
        self.status_pill.pack(side="right", padx=6)

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=20)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        # left: event feed
        left = tk.Frame(body, bg=PANEL, highlightthickness=1,
                        highlightbackground=LINE)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        head = tk.Frame(left, bg=PANEL, padx=14, pady=10)
        head.pack(fill="x")
        tk.Label(head, text="LIVE TRAFFIC", bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        self.feed_stats = tk.Label(head, text="0 events · 0 frames", bg=PANEL,
                                   fg=MUTED, font=("Segoe UI", 9))
        self.feed_stats.pack(side="right")
        self.feed = tk.Text(left, bg=PANEL2, fg=TEXT, relief="flat", bd=0,
                            font=MONO, state="disabled", wrap="none",
                            padx=12, pady=8, insertbackground=TEXT,
                            selectbackground=LINE)
        self.feed.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        for tag, color in (("tls", ACCENT), ("c2", ACCENT2), ("beacon", GOOD),
                           ("alert", BAD), ("info", MUTED), ("op", WARN)):
            self.feed.tag_configure(tag, foreground=color)
        self.feed.tag_configure("dim", foreground=MUTED)

        # right: control column
        right = tk.Frame(body, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)

        # -- campaign card
        card = tk.Frame(right, bg=PANEL, highlightthickness=1,
                        highlightbackground=LINE, padx=16, pady=14)
        card.grid(row=0, column=0, sticky="ew")
        tk.Label(card, text="CAMPAIGN", bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w",
                                                    columnspan=4)
        labels = [("Listener port", "port"), ("Campaign key", "camp"),
                  ("Beacon sleep (s)", "sleep"), ("Jitter %", "jitter")]
        self.vars = {}
        for i, (lab, key) in enumerate(labels):
            r, c = divmod(i, 2)
            tk.Label(card, text=lab, bg=PANEL, fg=MUTED,
                     font=("Segoe UI", 9)).grid(row=1 + r * 2, column=c * 2,
                                                sticky="w", pady=(8, 1))
            var = tk.StringVar(value={"port": "8443", "camp": "purple-night",
                                      "sleep": "8", "jitter": "25"}[key])
            self.vars[key] = var
            ent = tk.Entry(card, textvariable=var, bg=PANEL2, fg=TEXT,
                           relief="flat", insertbackground=TEXT, font=MONO,
                           width=16, highlightthickness=1,
                           highlightbackground=LINE, highlightcolor=ACCENT)
            ent.grid(row=2 + r * 2, column=c * 2, sticky="ew", padx=(0, 10))
        card.columnconfigure(1, weight=1)
        card.columnconfigure(3, weight=1)

        btns = tk.Frame(card, bg=PANEL)
        btns.grid(row=5, column=0, columnspan=4, sticky="ew", pady=(14, 0))
        self.start_btn = tk.Button(btns, text="▶  Start listener + beacon",
                                   command=self.start_lab, bg="#0e7490",
                                   fg="#e0faff", activebackground="#0891b2",
                                   activeforeground="white", relief="flat",
                                   font=FONT_B, padx=14, pady=8, cursor="hand2")
        self.start_btn.pack(side="left", fill="x", expand=True)
        self.stop_btn = tk.Button(btns, text="■  Stop", command=self.stop_lab,
                                  bg=PANEL2, fg=MUTED, activebackground=LINE,
                                  activeforeground=TEXT, relief="flat",
                                  font=FONT_B, padx=14, pady=8, state="disabled",
                                  cursor="hand2")
        self.stop_btn.pack(side="left", padx=(8, 0))

        # -- beacons card
        bcard = tk.Frame(right, bg=PANEL, highlightthickness=1,
                         highlightbackground=LINE)
        bcard.grid(row=1, column=0, sticky="nsew", pady=10)
        bhead = tk.Frame(bcard, bg=PANEL, padx=16, pady=10)
        bhead.pack(fill="x")
        tk.Label(bhead, text="REGISTERED BEACONS", bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        self.beacon_count = tk.Label(bhead, text="0", bg=PANEL, fg=MUTED,
                                     font=("Segoe UI", 9))
        self.beacon_count.pack(side="right")
        cols = ("host", "user", "pid", "os", "msgs")
        self.beacon_tree = ttk.Treeview(bcard, columns=cols, show="headings",
                                        height=5)
        for cid, text, w in (("host", "Host", 130), ("user", "User", 70),
                             ("pid", "PID", 60), ("os", "OS", 150),
                             ("msgs", "Msgs", 50)):
            self.beacon_tree.heading(cid, text=text)
            self.beacon_tree.column(cid, width=w, anchor="w")
        self.beacon_tree.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        # -- tasking card
        tcard = tk.Frame(right, bg=PANEL, highlightthickness=1,
                         highlightbackground=LINE, padx=16, pady=12)
        tcard.grid(row=2, column=0, sticky="ew")
        tk.Label(tcard, text="TASKING", bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        trow = tk.Frame(tcard, bg=PANEL)
        trow.pack(fill="x", pady=6)
        self.task_entry = tk.Entry(trow, bg=PANEL2, fg=TEXT, relief="flat",
                                   insertbackground=TEXT, font=MONO,
                                   highlightthickness=1, highlightbackground=LINE,
                                   highlightcolor=ACCENT)
        self.task_entry.pack(side="left", fill="x", expand=True)
        self.task_entry.insert(0, "whoami")
        tk.Button(trow, text="Queue", command=self.queue_task, bg="#7c3aed",
                  fg="white", activebackground="#8b5cf6", relief="flat",
                  font=FONT_B, padx=12, cursor="hand2").pack(side="left", padx=(8, 0))
        tk.Label(tcard, text="Whitelist: whoami · hostname · ipconfig · dir · tasklist · sleep N",
                 bg=PANEL, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w")

        # bottom: decryption lab
        bottom = tk.Frame(self, bg=BG, padx=20, pady=10)
        bottom.pack(fill="both")
        nb = ttk.Notebook(bottom)
        nb.pack(fill="both", expand=True)

        tab1 = tk.Frame(nb, bg=PANEL2)
        nb.add(tab1, text="  Decryption Lab  ")
        dl = tk.Frame(tab1, bg=PANEL2, padx=14, pady=10)
        dl.pack(fill="both", expand=True)
        dl.columnconfigure(1, weight=1)
        dl.rowconfigure(1, weight=1)

        tk.Label(dl, text="Passphrase", bg=PANEL2, fg=MUTED,
                 font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w")
        self.key_entry = tk.Entry(dl, bg=PANEL, fg=TEXT, relief="flat",
                                  insertbackground=TEXT, font=MONO, width=22,
                                  highlightthickness=1, highlightbackground=LINE,
                                  highlightcolor=ACCENT)
        self.key_entry.grid(row=0, column=0, sticky="ew", padx=(8, 10))
        self.key_entry.insert(0, "purple-night")
        tk.Button(dl, text="⏎  Decrypt frames", command=self.decrypt_frames,
                  bg="#0e7490", fg="#e0faff", activebackground="#0891b2",
                  relief="flat", font=FONT_B, padx=12, cursor="hand2"
                  ).grid(row=0, column=1, sticky="w")
        self.dec_summary = tk.Label(dl, text="no frames captured yet", bg=PANEL2,
                                    fg=MUTED, font=("Segoe UI", 9))
        self.dec_summary.grid(row=0, column=2, sticky="e", padx=(10, 0))

        # frame list + payload view
        panes = tk.Frame(dl, bg=PANEL2)
        panes.grid(row=1, column=0, columnspan=3, sticky="nsew", pady=(10, 0))
        panes.columnconfigure(0, weight=2)
        panes.columnconfigure(1, weight=3)
        panes.rowconfigure(0, weight=1)

        self.frame_list = tk.Listbox(panes, bg=PANEL2, fg=TEXT, relief="flat",
                                     font=MONO, selectbackground="#164e63",
                                     selectforeground="white", bd=0,
                                     highlightthickness=1,
                                     highlightbackground=LINE, exportselection=False)
        self.frame_list.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.frame_list.bind("<<ListboxSelect>>", self._on_frame_select)

        self.payload = tk.Text(panes, bg=PANEL, fg=TEXT, relief="flat", bd=0,
                               font=MONO_S, state="disabled", wrap="none",
                               padx=10, pady=8)
        self.payload.grid(row=0, column=1, sticky="nsew")
        ysb = ttk.Scrollbar(panes, orient="vertical", command=self.payload.yview)
        ysb.grid(row=0, column=2, sticky="ns")
        self.payload.configure(yscrollcommand=ysb.set)
        for tag, color in (("h", ACCENT), ("ok", GOOD), ("err", BAD),
                           ("dim", MUTED), ("data", TEXT)):
            self.payload.tag_configure(tag, foreground=color)

        tab2 = tk.Frame(nb, bg=PANEL2)
        nb.add(tab2, text="  Report Export  ")
        rep = tk.Frame(tab2, bg=PANEL2, padx=16, pady=14)
        rep.pack(fill="both", expand=True)
        tk.Label(rep, text="ANALYST REPORT", bg=PANEL2, fg=MUTED,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Label(rep, text="Generate a self-contained HTML report of this session: campaign metadata, event timeline, decrypted messages, detection notes and hexdumps.",
                 bg=PANEL2, fg=TEXT, font=FONT, wraplength=560,
                 justify="left").pack(anchor="w", pady=(4, 12))
        rrow = tk.Frame(rep, bg=PANEL2)
        rrow.pack(anchor="w")
        tk.Button(rrow, text="⬇  Generate & Save HTML Report",
                  command=self.download_report, bg="#0e7490", fg="#e0faff",
                  activebackground="#0891b2", relief="flat", font=FONT_B,
                  padx=14, pady=8, cursor="hand2").pack(side="left")
        tk.Button(rrow, text="⬇  Save Capture (.txt)", command=self.download_capture,
                  bg=PANEL, fg=TEXT, activebackground=LINE, relief="flat",
                  font=FONT_B, padx=14, pady=8, cursor="hand2").pack(side="left", padx=8)
        tk.Button(rrow, text="⬇  Save Recovered Plaintext",
                  command=self.download_plaintext, bg=PANEL, fg=TEXT,
                  activebackground=LINE, relief="flat", font=FONT_B,
                  padx=14, pady=8, cursor="hand2").pack(side="left")
        self.report_lbl = tk.Label(rep, text="", bg=PANEL2, fg=GOOD,
                                   font=("Segoe UI", 9))
        self.report_lbl.pack(anchor="w", pady=(10, 0))

    # -- helpers ---------------------------------------------------------------

    def _log(self, kind, msg):
        self.after(0, self._append_event, TrafficEvent(kind, "-- info", "", msg))

    def _append_event(self, e: TrafficEvent):
        self.event_seq += 1
        self.feed.configure(state="normal")
        color = {"tls": "tls", "c2": "c2", "beacon": "beacon", "alert": "alert",
                 "info": "dim", "op": "op"}.get(e.kind, "dim")
        self.feed.insert("end", "%s  %-8s %-9s %s\n" % (
            e.hhmmss, e.kind.upper()[:8], e.direction, e.summary), (color,))
        if float(self.feed.index("end-1c").split(".")[0]) > 800:
            self.feed.delete("1.0", "3.0")
        self.feed.configure(state="disabled")
        self.feed.see("end")
        n_ev = len(self.listener.snapshot_events()) if self.listener else self.event_seq
        n_fr = sum(1 for _, tag, _, _ in self.listener.pcap if tag == "packet") \
            if self.listener else 0
        self.feed_stats.configure(text="%d events · %d frames" % (n_ev, n_fr))

    def _poll_events(self):
        if self.listener:
            for e in self.listener.snapshot_events()[self.event_seq:]:
                self._append_event(e)
            self.captured_frames = [d for _, tag, _, d in self.listener.pcap
                                    if tag == "packet" and d[:4] == b"GLM1"]
            self.last_nonce = self.listener.last_nonce
            self._refresh_beacons()
            self.dec_summary.configure(
                text="%d frames in capture" % len(self.captured_frames))
        self.after(500, self._poll_events)

    def _refresh_beacons(self):
        if not self.listener:
            return
        known = self.listener.known_beacons
        existing = set(self.beacon_tree.get_children())
        for bid, reg in known.items():
            key = "b-%s" % bid
            vals = (reg.get("host"), reg.get("user"), reg.get("pid"),
                    reg.get("os"), "-")
            if key not in existing:
                self.beacon_tree.insert("", "end", iid=key, values=vals)
        self.beacon_count.configure(text=str(len(known)))

    # -- actions ----------------------------------------------------------------

    def start_lab(self):
        try:
            port = int(self.vars["port"].get())
            sleep = float(self.vars["sleep"].get())
            jitter = float(self.vars["jitter"].get()) / 100.0
            campaign = self.vars["camp"].get().strip() or "purple-night"
        except ValueError:
            messagebox.showerror("Bad input", "Port/sleep/jitter must be numeric.")
            return
        self.key_entry.delete(0, "end")
        self.key_entry.insert(0, campaign)

        self.listener = LabListener(host="127.0.0.1", port=port,
                                    campaign=campaign, log=self._log)
        try:
            self.listener.start()
        except OSError as exc:
            messagebox.showerror("Listener error",
                                 "Could not bind port %d:\n%s" % (port, exc))
            self.listener = None
            return
        self.status_pill.configure(text="● LISTENING  tls://127.0.0.1:%d" % port,
                                   fg=GOOD)

        b = beacon_mod.Beacon(host="127.0.0.1", port=port,
                              beacon_id="demo-implant", sleep_time=sleep,
                              jitter=jitter, campaign=campaign, log=self._log)
        b.start()
        self.beacons.append(b)

        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")

    def stop_lab(self):
        for b in self.beacons:
            b.stop()
        self.beacons.clear()
        if self.listener:
            self.listener.stop()
            self.status_pill.configure(text="● STOPPED", fg=WARN)
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")

    def queue_task(self):
        if not self.listener:
            messagebox.showinfo("Not running", "Start the listener first.")
            return
        cmd = self.task_entry.get().strip()
        if not cmd:
            return
        self.listener.queue_task("*", cmd)
        self.after(0, self._append_event, TrafficEvent(
            "op", "-- operator", "", "task queued: %s" % cmd))

    def decrypt_frames(self):
        if not self.captured_frames:
            messagebox.showinfo("Nothing to decrypt",
                                "Run a beacon session first so frames are captured.")
            return
        pw = self.key_entry.get().strip()
        nonce = self.last_nonce or b"\x00" * 8
        results, failures = decrypt_mod.decrypt_capture(self.captured_frames, pw, nonce)
        self._frame_map = {}
        self.frame_list.delete(0, "end")
        self.payload.configure(state="normal")
        self.payload.delete("1.0", "end")
        for i, r in enumerate(results):
            label = "%02d  %-8s %3dB  %s" % (i, r["msg_name"], len(r["plaintext"]),
                                             r["plaintext"].decode("utf-8", "replace")[:48]
                                             .replace("\n", " "))
            self.frame_list.insert("end", label)
            self._frame_map[str(i)] = None
        self.dec_summary.configure(
            text="%d decrypted · %d failed (wrong key or other session nonce)"
                 % (len(results), len(failures)),
            fg=GOOD if results else BAD)
        self._dec_results = results
        self._dec_failures = failures
        if results:
            self.frame_list.selection_set(0)
            self._show_frame(0)
        elif failures:
            self._show_failure(failures[0])

    def _on_frame_select(self, _evt=None):
        sel = self.frame_list.curselection()
        if sel:
            self._show_frame(sel[0])

    def _show_frame(self, idx):
        if not getattr(self, "_dec_results", None) or idx >= len(self._dec_results):
            return
        r = self._dec_results[idx]
        pt = r["plaintext"].decode("utf-8", "replace")
        self.payload.configure(state="normal")
        self.payload.delete("1.0", "end")
        self.payload.insert("end", "FRAME %d  ·  %s  ·  nonce=%s  ·  mac=%s\n"
                            % (idx, r["msg_name"], r["nonce"], r["mac"]), ("h",))
        self.payload.insert("end", "─" * 68 + "\n", ("dim",))
        self.payload.insert("end", "-- recovered plaintext " + "─" * 30 + "\n", ("dim",))
        self.payload.insert("end", pt + "\n\n", ("data",))
        self.payload.insert("end", "-- ciphertext hexdump " + "─" * 31 + "\n", ("dim",))
        self.payload.insert("end", hexdump(r["ciphertext"][:96]) + "\n\n", ("dim",))
        self.payload.insert("end", "-- header (magic|type|len|mac) " + "─" * 18 + "\n", ("dim",))
        self.payload.insert("end", r["header_hex"] + "\n", ("h",))
        self.payload.configure(state="disabled")

    def _show_failure(self, f):
        self.payload.configure(state="normal")
        self.payload.delete("1.0", "end")
        self.payload.insert("end", "DECRYPTION FAILED\n", ("err",))
        self.payload.insert("end", "─" * 68 + "\n", ("dim",))
        self.payload.insert("end", f["error"] + "\n\n", ("err",))
        self.payload.insert("end", f["hexdump"] + "\n", ("dim",))
        self.payload.configure(state="disabled")

    # -- exports -----------------------------------------------------------------

    def download_report(self):
        events = self.listener.snapshot_events() if self.listener else []
        frames = self.captured_frames
        nonce = self.last_nonce or b"\x00" * 8
        pw = self.key_entry.get().strip() or "purple-night"
        html = report_mod.build_report(pw, events, frames, nonce, pw)
        path = filedialog.asksaveasfilename(
            title="Save analyst report", defaultextension=".html",
            initialfile="GLM_Beacon_Lab_Report.html",
            filetypes=[("HTML report", "*.html")])
        if not path:
            return
        report_mod.write_report(html, path)
        self.report_lbl.configure(text="saved: %s" % path)
        import webbrowser
        webbrowser.open("file:///" + path.replace("\\", "/"))

    def download_capture(self):
        if not self.listener or not self.listener.pcap:
            messagebox.showinfo("Nothing to save", "No capture data yet.")
            return
        path = filedialog.asksaveasfilename(
            title="Save capture", defaultextension=".txt",
            initialfile="glm_capture.txt", filetypes=[("Text capture", "*.txt")])
        if not path:
            return
        self.listener.write_capture_text(path)
        self.report_lbl.configure(text="capture saved: %s" % path)

    def download_plaintext(self):
        results = getattr(self, "_dec_results", [])
        if not results:
            messagebox.showinfo("Nothing to save", "Decrypt frames first.")
            return
        path = filedialog.asksaveasfilename(
            title="Save recovered plaintext", defaultextension=".txt",
            initialfile="recovered_plaintext.txt",
            filetypes=[("Recovered plaintext", "*.txt")])
        if not path:
            return
        decrypt_mod.save_recovered(path, results)
        self.report_lbl.configure(text="plaintext saved: %s" % path)

    def _on_close(self):
        self.stop_lab()
        self.destroy()


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
