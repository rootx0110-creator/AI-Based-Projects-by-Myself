"""Main application window with beautiful tab-based UI."""
import os
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from ..core.scan_engine import ScanEngine, SCAN_MODE_FS, SCAN_MODE_RAW, SCAN_MODE_BOTH
from ..core.disk_reader import get_logical_drives, get_physical_disks, get_volumes, pretty_bytes
from ..utils.report import open_html_report, save_html_report

from .theme import (
    APP_NAME, APP_VERSION, APP_TAGLINE, COLORS, WINDOW_W, WINDOW_H,
    WINDOW_MIN_W, WINDOW_MIN_H, FONT_FAMILY,
)


def ck(var):
    """Chip preview: color preview square for file types."""
    return var


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.minsize(WINDOW_MIN_W, WINDOW_MIN_H)
        self.configure(fg_color=COLORS["bg"])

        self.selected_drive = None
        self.scan_result = None
        self.file_records = []
        self.scanning = False
        self._engine = None
        self._probe_thread = None
        self._recovery_stop = False

        self._build_layout()

        # Populate drives after UI is created
        self.after(120, self.refresh_drives)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_layout(self):
        self.grid_rowconfigure(0, weight=0)  # header: fixed
        self.grid_rowconfigure(1, weight=1)  # body: fills remaining space
        self.grid_rowconfigure(2, weight=0)  # status bar: fixed
        self.grid_columnconfigure(0, weight=1)

        self.header = self._build_header()
        self.header.grid(row=0, column=0, sticky="ew")

        body = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_rowconfigure(1, weight=1)
        body.grid_columnconfigure(0, weight=1)

        # ---- custom tab bar (top, full width, clean look) ----
        self.tab_bar = ctk.CTkFrame(body, fg_color="transparent")
        self.tab_bar.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 0))
        for i in range(5):
            self.tab_bar.grid_columnconfigure(i, weight=1)

        self.tab_buttons = {}
        tab_names = ["Disks", "Scan", "Results", "Recovery", "Report"]
        for i, name in enumerate(tab_names):
            btn = ctk.CTkButton(
                self.tab_bar, text=name,
                command=lambda n=name: self.show_tab(n),
                corner_radius=8, height=38,
                font=(FONT_FAMILY, 13, "bold"),
                fg_color=COLORS["card"], hover_color=COLORS["card_hover"],
                text_color=COLORS["muted"],
            )
            btn.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 4, 0))
            self.tab_buttons[name] = btn

        # ---- tab content container ----
        self.tab_content = ctk.CTkFrame(body, fg_color=COLORS["bg"], corner_radius=0)
        self.tab_content.grid(row=1, column=0, sticky="nsew", padx=16, pady=(4, 16))
        self.tab_content.grid_rowconfigure(0, weight=1)
        self.tab_content.grid_columnconfigure(0, weight=1)

        self.tab_pages = {}
        for name in tab_names:
            page = ctk.CTkFrame(self.tab_content, fg_color=COLORS["bg"], corner_radius=0)
            self.tab_pages[name] = page

        self._build_disks_tab(self.tab_pages["Disks"])
        self._build_scan_tab(self.tab_pages["Scan"])
        self._build_results_tab(self.tab_pages["Results"])
        self._build_recovery_tab(self.tab_pages["Recovery"])
        self._build_report_tab(self.tab_pages["Report"])

        self.show_tab("Disks")

        self.statusbar = self._build_statusbar()
        self.statusbar.grid(row=2, column=0, sticky="ew")

    def show_tab(self, name: str):
        """Switch visible tab page and restyle the tab buttons."""
        for page in self.tab_pages.values():
            page.grid_forget()
        self.tab_pages[name].grid(row=0, column=0, sticky="nsew")
        for n, btn in self.tab_buttons.items():
            selected = n == name
            btn.configure(
                fg_color=COLORS["accent"] if selected else COLORS["card"],
                hover_color=COLORS["accent2"] if selected else COLORS["card_hover"],
                text_color="#ffffff" if selected else COLORS["muted"],
            )

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=COLORS["panel"], corner_radius=0,
                              height=64)
        header.grid_propagate(False)
        header.grid_columnconfigure(0, weight=1)

        logo = ctk.CTkLabel(
            header, text="\U0001F9FA", font=(FONT_FAMILY, 26), text_color=COLORS["cyan"],
        )
        logo.grid(row=0, column=0, padx=(20, 8), pady=12, sticky="w")

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(
            title_box, text=APP_NAME, font=(FONT_FAMILY, 17, "bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_box, text=APP_TAGLINE, font=(FONT_FAMILY, 11),
            text_color=COLORS["muted"],
        ).pack(anchor="w")

        badge = ctk.CTkLabel(
            header, text=f"  v{APP_VERSION}  ",
            font=(FONT_FAMILY, 11, "bold"),
            fg_color=COLORS["card"], text_color=COLORS["accent"],
            corner_radius=12,
        )
        badge.grid(row=0, column=2, padx=20, sticky="e")
        return header

    def _build_statusbar(self):
        sb = ctk.CTkFrame(self, fg_color=COLORS["sidebar"], corner_radius=0, height=30)
        sb.grid_propagate(False)
        sb.grid_columnconfigure(0, weight=1)
        self.status_text = ctk.CTkLabel(
            sb, text="Ready  \u00b7  select a disk from the Disks tab",
            font=(FONT_FAMILY, 11), text_color=COLORS["muted"], anchor="w",
        )
        self.status_text.grid(row=0, column=0, sticky="ew", padx=14, pady=4)
        self.drive_status = ctk.CTkLabel(
            sb, text="No disk selected", font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["amber"], anchor="e",
        )
        self.drive_status.grid(row=0, column=1, padx=14, pady=4)
        return sb

    # ------------------------------------------------------------------
    # Disks Tab
    # ------------------------------------------------------------------
    def _build_disks_tab(self, parent):
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=3)
        parent.grid_columnconfigure(1, weight=1)

        # Left: drive list
        left = ctk.CTkFrame(parent, fg_color=COLORS["panel"], corner_radius=12)
        left.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 12), pady=0)
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=1)

        head = ctk.CTkFrame(left, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 6))
        ctk.CTkLabel(head, text="Available Drives", font=(FONT_FAMILY, 15, "bold"),
                     text_color=COLORS["text"]).pack(side="left")
        self.drive_count_label = ctk.CTkLabel(head, text="0 drives",
                                              font=(FONT_FAMILY, 11),
                                              text_color=COLORS["muted"])
        self.drive_count_label.pack(side="right")

        self.drive_tree = ctk.CTkScrollableFrame(left, fg_color="transparent")
        self.drive_tree.grid(row=1, column=0, sticky="nsew", padx=12, pady=6)

        btn_row = ctk.CTkFrame(left, fg_color="transparent")
        btn_row.grid(row=2, column=0, sticky="ew", padx=12, pady=(6, 14))
        ctk.CTkButton(
            btn_row, text="\u21bb  Refresh", command=self.refresh_drives,
            fg_color=COLORS["card"], hover_color=COLORS["card_hover"],
            text_color=COLORS["text"], corner_radius=8,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            btn_row, text="Select", command=self.on_select_drive,
            fg_color=COLORS["accent"], hover_color=COLORS["accent2"],
            corner_radius=8, font=(FONT_FAMILY, 12, "bold"),
        ).pack(side="right")

        # Right: disk details
        right = ctk.CTkFrame(parent, fg_color=COLORS["panel"], corner_radius=12)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(right, text="Disk Details",
                     font=(FONT_FAMILY, 15, "bold"), text_color=COLORS["text"]
                     ).pack(anchor="w", padx=18, pady=(16, 10))

        self.detail_frame = ctk.CTkFrame(right, fg_color=COLORS["card"], corner_radius=10)
        self.detail_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        for i in range(4):
            self.detail_frame.grid_columnconfigure(0, weight=1)
        self._detail_labels = {}
        rows = ["Device", "Type", "Size", "Filesystem", "Volume Name", "Raw Path"]
        for i, label in enumerate(rows):
            self.detail_frame.grid_rowconfigure(i, weight=0)
            ctk.CTkLabel(self.detail_frame, text=label.upper(),
                         font=(FONT_FAMILY, 10, "bold"), text_color=COLORS["muted"],
                         anchor="w").grid(row=i, column=0, sticky="ew",
                                          padx=14, pady=(10 if i == 0 else 0, 0))
            val = ctk.CTkLabel(self.detail_frame, text="\u2014",
                               font=(FONT_FAMILY, 13), text_color=COLORS["text"],
                               anchor="w", wraplength=300)
            val.grid(row=i, column=1, sticky="ew", padx=14, pady=(8 if i == 0 else 0, 0))
            self._detail_labels[label] = val

        warn = ctk.CTkLabel(
            right,
            text="\u26a0  Raw disk access requires the app "
                 "to be run as Administrator for full recovery capability.",
            font=(FONT_FAMILY, 11), text_color=COLORS["amber"],
            wraplength=340,
        )
        warn.pack(anchor="w", padx=16, pady=(0, 14))

        self.drive_cards = {}

    def refresh_drives(self):
        cols = get_logical_drives()
        phy = get_physical_disks()
        for d in cols + phy:
            if not d.encoded_path:
                d.encoded_path = f"\\\\.\\{d.letter}:"
        self.drives = cols + phy

        for w in self.drive_tree.winfo_children():
            w.destroy()
        self.drive_cards.clear()

        if not self.drives:
            ctk.CTkLabel(self.drive_tree, text="No drives detected.",
                         text_color=COLORS["muted"]).pack(pady=30)
            self.drive_count_label.configure(text="0 drives")
            return

        self.drive_count_label.configure(text=f"{len(self.drives)} drives")
        for d in self.drives:
            self._add_drive_card(d)

        # Auto-select first logical drive
        if self.selected_drive is None and self.drives:
            self.on_select_card(self.drives[0])
            # select its radio
            self.show_tab("Disks")

    def _add_drive_card(self, drive):
        card = ctk.CTkFrame(self.drive_tree, fg_color=COLORS["card"], corner_radius=10,
                            cursor="hand2")
        card.pack(fill="x", pady=4, padx=2)
        card.grid_columnconfigure(1, weight=1)

        icon = "\U0001F4BE" if drive.letter else "\U0001F5A5"
        ctk.CTkLabel(card, text=icon, font=(FONT_FAMILY, 22),
                     text_color=COLORS["cyan"]).grid(row=0, column=0, rowspan=3,
                                                     padx=(14, 10), pady=10)
        title = drive.name if drive.name else f"{drive.letter}:"
        ctk.CTkLabel(card, text=title, font=(FONT_FAMILY, 14, "bold"),
                     text_color=COLORS["text"]).grid(row=0, column=1, sticky="w",
                                                     pady=(10, 0))
        sub = drive.file_system_hint or "Unknown FS"
        if drive.is_removable:
            sub += "  \u00b7  Removable"
        ctk.CTkLabel(card, text=sub, font=(FONT_FAMILY, 11),
                     text_color=COLORS["muted"]).grid(row=1, column=1, sticky="w")
        ctk.CTkLabel(card, text=pretty_bytes(drive.size_bytes),
                     font=(FONT_FAMILY, 12, "bold"),
                     text_color=COLORS["teal"]).grid(row=2, column=1, sticky="w",
                                                     pady=(0, 10))

        check = ctk.CTkRadioButton(
            card, text="", width=16, command=lambda d=drive: self.on_select_card(d),
            radiobutton_width=18, radiobutton_height=18,
            fg_color=COLORS["accent"], hover_color=COLORS["accent2"],
            border_color=COLORS["border"],
        )
        check.grid(row=0, column=2, rowspan=3, padx=14, pady=10)
        card.bind("<Button-1>", lambda e, d=drive: self.on_select_card(d))
        for child in card.winfo_children():
            child.bind("<Button-1>", lambda e, d=drive: self.on_select_card(d))
        self.drive_cards[drive.encoded_path] = (card, check)

    def on_select_card(self, drive):
        self.selected_drive = drive
        for (card, check) in self.drive_cards.values():
            check.deselect()
        if drive.encoded_path in self.drive_cards:
            self.drive_cards[drive.encoded_path][1].select()
        self._update_details(drive)
        self.drive_status.configure(text=f"Selected: {drive.name or drive.letter}")
        self.status_text.configure(text="Disk selected \u2014 configure & start a scan")

    def _update_details(self, drive):
        mapping = {
            "Device": drive.name or (drive.letter + ":"),
            "Type": ("Physical Disk" if not drive.letter else
                     ("Removable Drive" if drive.is_removable else "Logical Drive")),
            "Size": pretty_bytes(drive.size_bytes),
            "Filesystem": drive.file_system_hint or "Detect on scan",
            "Volume Name": drive.volume_name or "\u2014",
            "Raw Path": drive.encoded_path,
        }
        for k, v in mapping.items():
            if k in self._detail_labels:
                self._detail_labels[k].configure(text=v)

    def on_select_drive(self):
        if self.selected_drive:
            self.show_tab("Scan")
            self.status_text.configure(
                text=f"Scanning target: {self.selected_drive.name or self.selected_drive.letter}")

    # ------------------------------------------------------------------
    # Scan Tab
    # ------------------------------------------------------------------
    def _build_scan_tab(self, parent):
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=1)

        # Left column: configuration
        left = ctk.CTkFrame(parent, fg_color=COLORS["panel"], corner_radius=12)
        left.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 12))

        ctk.CTkLabel(left, text="Scan Configuration",
                     font=(FONT_FAMILY, 15, "bold"), text_color=COLORS["text"]
                     ).pack(anchor="w", padx=18, pady=(16, 8))

        cfg = ctk.CTkFrame(left, fg_color=COLORS["card"], corner_radius=10)
        cfg.pack(fill="x", padx=16, pady=(0, 12))

        self.scan_target_label = ctk.CTkLabel(
            cfg, text="Target:  None selected",
            font=(FONT_FAMILY, 12), text_color=COLORS["text"], anchor="w",
        )
        self.scan_target_label.pack(fill="x", padx=16, pady=(14, 4))

        ctk.CTkLabel(cfg, text="Scan Mode",
                     font=(FONT_FAMILY, 11, "bold"), text_color=COLORS["muted"],
                     anchor="w").pack(fill="x", padx=16, pady=(10, 2))

        self.scan_mode = tk.StringVar(value="both")
        modes = [("filesystem", "Filesystem (FAT/NTFS)", "Parse directory tables & $MFT for deleted entries"),
                 ("raw", "Raw Carving only", "Scan sectors for file signatures"),
                 ("both", "Quick Scan (FS + Raw)", "Recommended - fastest comprehensive pass")]
        for val, label, desc in modes:
            row = ctk.CTkFrame(cfg, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=2)
            ctk.CTkRadioButton(
                row, text=label, variable=self.scan_mode, value=val,
                font=(FONT_FAMILY, 12), fg_color=COLORS["accent"],
                hover_color=COLORS["accent2"], text_color=COLORS["text"],
            ).pack(side="left", anchor="w")
            ctk.CTkLabel(row, text=desc, font=(FONT_FAMILY, 10),
                         text_color=COLORS["muted"]).pack(side="right", padx=8)

        ctk.CTkLabel(cfg, text="Max MFT Records (NTFS)",
                     font=(FONT_FAMILY, 11, "bold"), text_color=COLORS["muted"],
                     anchor="w").pack(fill="x", padx=16, pady=(10, 2))
        self.mft_var = tk.StringVar(value="200000")
        ctk.CTkEntry(cfg, textvariable=self.mft_var, height=34,
                     corner_radius=8, border_color=COLORS["border"],
                     fg_color=COLORS["panel"], text_color=COLORS["text"])\
            .pack(fill="x", padx=16, pady=(0, 8))

        btn_row = ctk.CTkFrame(left, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(4, 6))
        self.start_btn = ctk.CTkButton(
            btn_row, text="\u25b6  Start Scan", command=self.start_scan,
            fg_color=COLORS["green"], hover_color="#16a085", corner_radius=8,
            font=(FONT_FAMILY, 13, "bold"), height=40, text_color="#06231a",
        )
        self.start_btn.pack(side="left", fill="x", expand=True)
        self.stop_btn = ctk.CTkButton(
            btn_row, text="\u25a0 Stop", command=self.stop_scan,
            fg_color=COLORS["red"], hover_color="#c0392b", corner_radius=8,
            font=(FONT_FAMILY, 13, "bold"), height=40, state="disabled",
        )
        self.stop_btn.pack(side="left", padx=(8, 0), fill="x", expand=True)

        # Right: progress panel
        right = ctk.CTkFrame(parent, fg_color=COLORS["panel"], corner_radius=12)
        right.grid(row=0, column=1, rowspan=2, sticky="nsew")
        right.grid_rowconfigure(4, weight=1)
        right.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(right, text="Scan Progress",
                     font=(FONT_FAMILY, 15, "bold"), text_color=COLORS["text"]
                     ).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 4))

        self.stage_label = ctk.CTkLabel(
            right, text="Waiting to start\u2026",
            font=(FONT_FAMILY, 12), text_color=COLORS["muted"], anchor="w",
        )
        self.stage_label.grid(row=1, column=0, sticky="ew", padx=18, pady=(4, 2))

        self.progress = ctk.CTkProgressBar(
            right, width=400, height=12, corner_radius=6,
            fg_color=COLORS["card"], progress_color=COLORS["accent"],
        )
        self.progress.grid(row=2, column=0, sticky="ew", padx=18, pady=(6, 4))
        self.progress.set(0)

        self.progress_detail = ctk.CTkLabel(
            right, text="", font=(FONT_FAMILY, 10), text_color=COLORS["muted"],
            anchor="w",
        )
        self.progress_detail.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 4))

        log_box = ctk.CTkFrame(right, fg_color=COLORS["card"], corner_radius=10)
        log_box.grid(row=4, column=0, sticky="nsew", padx=16, pady=(10, 16))
        log_box.grid_rowconfigure(1, weight=1)
        log_box.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(log_box, text="Activity Log", font=(FONT_FAMILY, 11, "bold"),
                     text_color=COLORS["muted"]).grid(row=0, column=0, sticky="w",
                                                      padx=12, pady=(8, 0))
        self.log_text = tk.Text(
            log_box, bg=COLORS["sidebar"], fg=COLORS["text"], insertbackground=COLORS["text"],
            font=(FONT_FAMILY, 11), relief="flat", height=12, wrap="word",
        )
        self.log_text.grid(row=1, column=0, sticky="nsew", padx=10, pady=8)
        self.log_text.configure(state="disabled")

    def _log(self, msg):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _set_progress(self, stage, current, total, msg=""):
        def _do():
            stage_names = {
                "fat": "Scanning FAT directory entries",
                "ntfs": "Scanning NTFS $MFT records",
                "raw": "Raw signature carving",
                "done": "Scan complete",
                "error": "Scan error",
            }
            label = stage_names.get(stage, stage)
            self.stage_label.configure(text=f"{label}  \u2026")
            if msg:
                self.stage_label.configure(text=f"{label}\n{msg}")
            self._log(f"{label} {msg}".strip())
            if stage == "done":
                self.progress.set(1.0)
                self.start_btn.configure(state="normal")
                self.stop_btn.configure(state="disabled")
                self.progress_detail.configure(text="100% \u2014 complete")
                self._finalize_scan()
            elif stage == "error":
                self._log(f"ERROR: {msg}")
                self.start_btn.configure(state="normal")
                self.stop_btn.configure(state="disabled")
            elif stage == "raw":
                if total:
                    frac = min(current / total, 1.0)
                    self.progress.set(frac)
                    self.progress_detail.configure(
                        text=f"{current // (1024*1024)} MB / {total // (1024*1024)} MB scanned")
            else:
                self.progress.set(0.3 + (0.0002 * (current % 2000)))
                self.progress_detail.configure(text=f"{current:,} entries scanned")
        self.after(10, _do)

    def start_scan(self):
        if not self.selected_drive:
            messagebox.showwarning("No Disk", "Please select a disk from the Disks tab first.")
            self.show_tab("Disks")
            return
        try:
            os.environ["PYTHONPATH"]  # no-op
        except Exception:
            pass
        self.scanning = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.progress.set(0)
        self.stage_label.configure(text="Starting scan\u2026")
        self._log(f"Scan started on {self.selected_drive.name or self.selected_drive.letter}")
        mode = self.scan_mode.get()
        try:
            mft_count = int(self.mft_var.get())
        except ValueError:
            mft_count = 200000

        self._engine = ScanEngine(
            self.selected_drive.encoded_path,
            progress_cb=self._set_progress,
            status_cb=lambda t: self.stage_label.after(1, lambda: self.stage_label.configure(text=t)),
        )
        self._engine.start(mode=mode, max_ntfs_records=mft_count)

    def stop_scan(self):
        if self._engine:
            self._log("Stop requested \u2014 finishing current pass\u2026")
            self._engine.stop()
            self.stop_btn.configure(state="disabled")

    def _finalize_scan(self):
        self.scanning = False
        result = self._engine.result if self._engine else None
        self.scan_result = result
        self.file_records = []
        if result:
            for f in result.deleted_files:
                if hasattr(f, "to_dict"):
                    self.file_records.append(f.to_dict())
                else:
                    self.file_records.append(f)
            for f in result.carved_files:
                if hasattr(f, "to_dict"):
                    self.file_records.append(f.to_dict())
                else:
                    self.file_records.append(f)
            if result.error:
                self._log(f"Scan ended with error: {result.error}")
        self._log(f"Found {len(self.file_records)} recoverable items.")
        self._refresh_results_table()
        self._update_recovery_summary()
        self._enable_report_buttons()
        self.show_tab("Results")

    # ------------------------------------------------------------------
    # Results Tab
    # ------------------------------------------------------------------
    def _build_results_tab(self, parent):
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        toolbar = ctk.CTkFrame(parent, fg_color=COLORS["panel"], corner_radius=12)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        toolbar.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(toolbar, text="Search:",
                     font=(FONT_FAMILY, 12), text_color=COLORS["muted"])\
            .grid(row=0, column=0, padx=(16, 6), pady=12)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._filter_results())
        self.search_entry = ctk.CTkEntry(
            toolbar, textvariable=self.search_var, width=260, height=32,
            corner_radius=8, placeholder_text="Filter by name\u2026",
            border_color=COLORS["border"], fg_color=COLORS["card"],
            text_color=COLORS["text"],
        )
        self.search_entry.grid(row=0, column=1, padx=(0, 10), pady=12)

        self.result_count_label = ctk.CTkLabel(
            toolbar, text="0 items", font=(FONT_FAMILY, 12, "bold"),
            text_color=COLORS["teal"],
        )
        self.result_count_label.grid(row=0, column=3, padx=14, pady=12)

        table_frame = ctk.CTkFrame(parent, fg_color=COLORS["panel"], corner_radius=12)
        table_frame.grid(row=1, column=0, sticky="nsew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        style = tk.ttk.Style()
        style.theme_use("clam")
        try:
            style.configure("Tre.Treeview",
                            background=COLORS["sidebar"],
                            fieldbackground=COLORS["sidebar"],
                            foreground=COLORS["text"],
                            rowheight=30,
                            borderwidth=0,
                            font=(FONT_FAMILY, 11))
            style.configure("Tre.Treeview.Heading",
                            background=COLORS["card"],
                            foreground=COLORS["muted"],
                            borderwidth=0,
                            font=(FONT_FAMILY, 11, "bold"))
            style.map("Tre.Treeview.Heading",
                      background=[("active", COLORS["card_hover"])])
            style.map("Tre.Treeview",
                      background=[("selected", COLORS["accent"])],
                      foreground=[("selected", "#ffffff")])
        except Exception:
            pass

        cols = ("type", "name", "size", "fs", "status", "path")
        self.results_tree = tk.ttk.Treeview(
            table_frame, columns=cols, show="headings",
            style="Tre.Treeview", selectmode="extended",
        )
        headers = {
            "type": ("Type", 90, "center"),
            "name": ("File Name", 340, "w"),
            "size": ("Size", 100, "e"),
            "fs": ("FS", 70, "center"),
            "status": ("Status", 110, "center"),
            "path": ("Location", 340, "w"),
        }
        for cid, (t, w, m) in headers.items():
            self.results_tree.heading(cid, text=t)
            self.results_tree.column(cid, width=w, anchor=m)

        vsb = tk.ttk.Scrollbar(table_frame, orient="vertical",
                               command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=vsb.set)
        self.results_tree.grid(row=0, column=0, sticky="nsew", padx=(12, 0), pady=12)
        vsb.grid(row=0, column=1, sticky="ns", padx=(0, 12), pady=12)

        self._all_rows = []
        self.results_tree.tag_configure("deleted", foreground=COLORS["amber"])
        self.results_tree.tag_configure("carved", foreground=COLORS["red"])

    def _refresh_results_table(self):
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        self._all_rows = []
        for rec in self.file_records:
            size = rec.get("size")
            size_txt = pretty_bytes(size) if isinstance(size, int) and size else "-"
            tagname = "deleted" if (rec.get("status") or "").lower() == "deleted" else "carved"
            rowvals = (
                (rec.get("extension") or "other").upper(),
                rec.get("full_name") or rec.get("name") or "",
                size_txt,
                rec.get("fs") or "?",
                rec.get("status") or "",
                rec.get("first_offset") or "",
            )
            self._all_rows.append(rowvals)
            self.results_tree.insert("", "end", values=rowvals, tags=(tagname,))
        self.result_count_label.configure(text=f"{len(self._all_rows):,} items")
        self._filter_results()

    def _filter_results(self):
        q = self.search_var.get().lower()
        if q:
            n = 0
            for i in self.results_tree.get_children():
                self.results_tree.delete(i)
            for rv in self._all_rows:
                if q in rv[1].lower():
                    tagname = "deleted" if rv[4].lower() == "deleted" else "carved"
                    self.results_tree.insert("", "end", values=rv, tags=(tagname,))
                    n += 1
            self.result_count_label.configure(text=f"{n:,} filtered")
        else:
            self.result_count_label.configure(text=f"{len(self._all_rows):,} items")

    # ------------------------------------------------------------------
    # Recovery Tab
    # ------------------------------------------------------------------
    def _build_recovery_tab(self, parent):
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(parent, fg_color=COLORS["panel"], corner_radius=12)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        top.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(top, text="Destination folder:",
                     font=(FONT_FAMILY, 12), text_color=COLORS["muted"])\
            .grid(row=0, column=0, padx=(16, 6), pady=14)
        self.recovery_dir_var = tk.StringVar(value=os.path.join(
            os.path.expanduser("~"), "Documents", "Recovered_Files"))
        self.recovery_dir_entry = ctk.CTkEntry(
            top, textvariable=self.recovery_dir_var, height=34, corner_radius=8,
            border_color=COLORS["border"], fg_color=COLORS["card"],
            text_color=COLORS["text"],
        )
        self.recovery_dir_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=14)
        ctk.CTkButton(
            top, text="Browse\u2026", command=self._browse_recovery_dir,
            fg_color=COLORS["card"], hover_color=COLORS["card_hover"],
            text_color=COLORS["text"], corner_radius=8,
        ).grid(row=0, column=2, padx=14, pady=14)

        mid = ctk.CTkFrame(parent, fg_color=COLORS["panel"], corner_radius=12)
        mid.grid(row=1, column=0, sticky="nsew")
        mid.grid_rowconfigure(0, weight=1)
        mid.grid_columnconfigure(0, weight=1)

        style = tk.ttk.Style()
        try:
            style.configure("Rec.Treeview",
                            background=COLORS["sidebar"],
                            fieldbackground=COLORS["sidebar"],
                            foreground=COLORS["text"],
                            rowheight=28, borderwidth=0, font=(FONT_FAMILY, 11))
            style.configure("Rec.Treeview.Heading",
                            background=COLORS["card"], foreground=COLORS["muted"],
                            borderwidth=0, font=(FONT_FAMILY, 11, "bold"))
            style.map("Rec.Treeview.Heading",
                      background=[("active", COLORS["card_hover"])])
            style.map("Rec.Treeview",
                      background=[("selected", COLORS["accent"])],
                      foreground=[("selected", "#ffffff")])
        except Exception:
            pass
        cols = ("pick", "name", "ext", "size", "fs", "status")
        self.recovery_tree = tk.ttk.Treeview(
            mid, columns=cols, show="headings", style="Rec.Treeview",
            selectmode="extended",
        )
        headers = {
            "pick": ("Select", 55, "center"),
            "name": ("File Name", 400, "w"),
            "ext": ("Type", 90, "center"),
            "size": ("Size", 100, "e"),
            "fs": ("FS", 70, "center"),
            "status": ("Status", 100, "center"),
        }
        for cid, (t, w, m) in headers.items():
            self.recovery_tree.heading(cid, text=t)
            self.recovery_tree.column(cid, width=w, anchor=m, stretch=(cid != "pick"))
        vsb = tk.ttk.Scrollbar(mid, orient="vertical",
                               command=self.recovery_tree.yview)
        self.recovery_tree.configure(yscrollcommand=vsb.set)
        self.recovery_tree.grid(row=0, column=0, sticky="nsew", padx=(12, 0), pady=12)
        vsb.grid(row=0, column=1, sticky="ns", padx=(0, 12), pady=12)
        self.recovery_tree.tag_configure("deleted", foreground=COLORS["amber"])
        self.recovery_tree.tag_configure("carved", foreground=COLORS["red"])
        self.recovery_tree.bind("<Button-1>", self._on_recovery_click)

        bottom = ctk.CTkFrame(parent, fg_color=COLORS["panel"], corner_radius=12)
        bottom.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        bottom.grid_columnconfigure(4, weight=1)

        self.recovery_summary = ctk.CTkLabel(
            bottom, text="0 selected", font=(FONT_FAMILY, 12, "bold"),
            text_color=COLORS["teal"],
        )
        self.recovery_summary.grid(row=0, column=0, padx=16, pady=14, sticky="w")

        ctk.CTkButton(
            bottom, text="Select All", command=self._recovery_select_all,
            fg_color=COLORS["card"], hover_color=COLORS["card_hover"],
            text_color=COLORS["text"], corner_radius=8,
            font=(FONT_FAMILY, 12, "bold"), width=96,
        ).grid(row=0, column=1, padx=(0, 6), pady=12)
        ctk.CTkButton(
            bottom, text="Clear", command=self._recovery_clear_all,
            fg_color=COLORS["card"], hover_color=COLORS["card_hover"],
            text_color=COLORS["text"], corner_radius=8,
            font=(FONT_FAMILY, 12, "bold"), width=96,
        ).grid(row=0, column=2, padx=6, pady=12)

        self._recovery_progress = ctk.CTkProgressBar(
            bottom, width=180, height=10, corner_radius=5,
            fg_color=COLORS["card"], progress_color=COLORS["teal"],
        )
        self._recovery_progress.grid(row=0, column=3, padx=12, pady=14, sticky="ew")
        self._recovery_progress.set(0)

        self.recover_btn = ctk.CTkButton(
            bottom, text="\U0001F504  Recover Selected", command=self.recover_selected,
            fg_color=COLORS["green"], hover_color="#16a085", text_color="#06231a",
            corner_radius=8, font=(FONT_FAMILY, 13, "bold"), height=40,
        )
        self.recover_btn.grid(row=0, column=5, padx=16, pady=12)

    def _browse_recovery_dir(self):
        path = filedialog.askdirectory(initialdir=self.recovery_dir_var.get() or None,
                                       title="Choose recovery destination")
        if path:
            self.recovery_dir_var.set(path)

    def _update_recovery_summary(self):
        for item in self.recovery_tree.get_children():
            self.recovery_tree.delete(item)
        for rec in self.file_records:
            size = rec.get("size")
            size_txt = pretty_bytes(size) if isinstance(size, int) and size else "-"
            tagname = "deleted" if (rec.get("status") or "").lower() == "deleted" else "carved"
            self.recovery_tree.insert("", "end", values=(
                "[ ]",
                rec.get("full_name") or rec.get("name") or "",
                (rec.get("extension") or "other").upper(),
                size_txt,
                rec.get("fs") or "?",
                rec.get("status") or "",
            ), tags=(tagname,))
        self._refresh_recovery_selection_count()

    def _on_recovery_click(self, event):
        if self.recovery_tree.identify_region(event.x, event.y) == "cell":
            self.toggle_recovery_selection()

    def toggle_recovery_selection(self):
        item = self.recovery_tree.focus()
        if not item:
            return
        vals = list(self.recovery_tree.item(item, "values"))
        vals[0] = "[x]" if vals[0] == "[ ]" else "[ ]"
        self.recovery_tree.item(item, values=vals)
        tag = "deleted" if vals[5].lower() == "deleted" else "carved"
        self.recovery_tree.item(item, tags=(tag,))
        self._refresh_recovery_selection_count()

    def _recovery_select_all(self):
        for item in self.recovery_tree.get_children():
            vals = list(self.recovery_tree.item(item, "values"))
            vals[0] = "[x]"
            self.recovery_tree.item(item, values=vals)
        self._refresh_recovery_selection_count()

    def _recovery_clear_all(self):
        for item in self.recovery_tree.get_children():
            vals = list(self.recovery_tree.item(item, "values"))
            vals[0] = "[ ]"
            self.recovery_tree.item(item, values=vals)
        self._refresh_recovery_selection_count()

    def _refresh_recovery_selection_count(self):
        n = 0
        for item in self.recovery_tree.get_children():
            if self.recovery_tree.item(item, "values")[0] == "[x]":
                n += 1
        self.recovery_summary.configure(text=f"{n} file(s) selected for recovery")

    def recover_selected(self):
        selected = []
        for item in self.recovery_tree.get_children():
            vals = self.recovery_tree.item(item, "values")
            if vals[0] == "[x]":
                selected.append(vals)
        if not selected:
            messagebox.showinfo("Nothing Selected",
                                "Tick files in the list, then click Recover.")
            return
        dest = self.recovery_dir_var.get().strip()
        if not dest:
            messagebox.showwarning("No Destination", "Choose a destination folder first.")
            return
        os.makedirs(dest, exist_ok=True)

        self.recover_btn.configure(state="disabled", text="Recovering\u2026")
        self._recovery_progress.set(0)
        threading.Thread(target=self._do_recovery, args=(selected, dest),
                         daemon=True).start()

    def _do_recovery(self, selected, dest):
        from ..core.recovery import RecoveryEngine
        from ..core.disk_reader import DiskReader
        from ..core.fat_parser import parse_fat_info
        from ..core.ntfs_parser import parse_ntfs_boot

        # Map the display rows back to the actual record objects by full name
        index = {}
        result = self.scan_result
        for f in (result.deleted_files if result else []):
            if hasattr(f, "full_name"):
                index.setdefault(f.full_name, []).append(f)
        for f in (result.carved_files if result else []):
            index.setdefault(f.name, []).append(f)

        ok, fail = 0, 0
        total = len(selected)
        try:
            reader = DiskReader(self.selected_drive.encoded_path)
        except PermissionError as e:
            self.after(0, lambda: messagebox.showerror("Access Denied", str(e)))
            self.after(0, lambda: self.recover_btn.configure(
                state="normal", text="\U0001F504  Recover Selected"))
            return

        engine = RecoveryEngine(reader)
        fs = None
        boot = None
        try:
            if result:
                if result.fat_info:
                    fs = result.fat_info
                if result.ntfs_boot:
                    boot = result.ntfs_boot
        except Exception:
            pass

        for i, vals in enumerate(selected):
            name = vals[1]
            status = vals[5]
            record = None
            candidates = index.get(name)
            if candidates:
                record = candidates[0]
            outname = self._safe_recovery_name(name, i)
            outpath = os.path.join(dest, outname)
            try:
                written = None
                if status.lower() == "deleted" and hasattr(record, "start_cluster"):
                    if fs:
                        written = engine.recover_fat_to_file(
                            fs, record.start_cluster, record.size, outpath)
                elif status.lower() == "deleted" and hasattr(record, "mft_index"):
                    if boot:
                        written = engine.recover_ntfs_to_file(boot, record, outpath)
                elif status.lower() == "carved" and hasattr(record, "offset"):
                    written = engine.carve_raw_file(record.offset, record.size, outpath)
                if written:
                    ok += 1
                else:
                    fail += 1
            except Exception:
                fail += 1
            frac = (i + 1) / total if total else 1
            self.after(1, lambda f=frac: self._recovery_progress.set(f))
        reader.close()
        self.after(0, lambda: self._recovery_done(ok, fail))

    def _safe_recovery_name(self, name, i):
        base = os.path.basename(str(name).replace("/", os.sep))
        base = "".join(c for c in base if c not in '\\/:*?"<>|') or f"file_{i}"
        if os.path.exists(os.path.join(self.recovery_dir_var.get(), base)):
            stem, ext = os.path.splitext(base)
            base = f"{stem}_{i}{ext}"
        return base

    def _recovery_done(self, ok, fail):
        self._recovery_progress.set(1.0)
        self.recover_btn.configure(state="normal", text="\U0001F504  Recover Selected")
        self._log(f"Recovery finished: {ok} succeed, {fail} failed")
        messagebox.showinfo(
            "Recovery Complete",
            f"Successfully recovered {ok} file(s).\n" +
            (f"{fail} file(s) could not be recovered." if fail else "") +
            f"\n\nSaved to:\n{self.recovery_dir_var.get()}",
        )

    # ------------------------------------------------------------------
    # Report Tab
    # ------------------------------------------------------------------
    def _build_report_tab(self, parent):
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        hero = ctk.CTkFrame(parent, fg_color=COLORS["panel"], corner_radius=14)
        hero.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        hero.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(hero, text="\U0001F4C4", font=(FONT_FAMILY, 42),
                     text_color=COLORS["cyan"]).grid(row=0, column=0, padx=18,
                                                     pady=(18, 2))
        ctk.CTkLabel(hero, text="Generate & Download Report",
                     font=(FONT_FAMILY, 16, "bold"), text_color=COLORS["text"])\
            .grid(row=0, column=1, sticky="w", pady=(18, 0))
        ctk.CTkLabel(
            hero,
            text="Produce a full HTML report of the last scan featuring "
                 "summary statistics, filesystem details, file-type analysis and the complete "
                 "recovered-file list. Reports open in your browser and can be saved or printed.",
            font=(FONT_FAMILY, 12), text_color=COLORS["muted"],
            wraplength=700, justify="left",
        ).grid(row=1, column=1, sticky="w", padx=(0, 18), pady=(2, 20))

        body = ctk.CTkFrame(parent, fg_color=COLORS["panel"], corner_radius=14)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)

        self.report_info_label = ctk.CTkLabel(
            body,
            text="No scan data available yet.\nRun a scan first, then generate a report.",
            font=(FONT_FAMILY, 12), text_color=COLORS["muted"], justify="center",
        )
        self.report_info_label.grid(row=0, column=0, pady=24, padx=16)

        actions = ctk.CTkFrame(body, fg_color="transparent")
        actions.grid(row=1, column=0, pady=(0, 20))
        self.report_open_btn = ctk.CTkButton(
            actions, text="\U0001F5A9  Open in Browser", command=self.generate_report_open,
            fg_color=COLORS["accent"], hover_color=COLORS["accent2"],
            corner_radius=8, font=(FONT_FAMILY, 13, "bold"), height=42,
            state="disabled",
        )
        self.report_open_btn.pack(side="left", padx=6)
        self.report_save_btn = ctk.CTkButton(
            actions, text="\U0001F4BE  Save Report\u2026", command=self.generate_report_save,
            fg_color=COLORS["card"], hover_color=COLORS["card_hover"],
            text_color=COLORS["text"], corner_radius=8,
            font=(FONT_FAMILY, 13, "bold"), height=42, state="disabled",
        )
        self.report_save_btn.pack(side="left", padx=6)

    def _report_details(self):
        return self.file_records

    def _enable_report_buttons(self):
        has = bool(self.scan_result and self.file_records)
        state = "normal" if has else "disabled"
        self.report_open_btn.configure(state=state)
        self.report_save_btn.configure(state=state)
        if has:
            fs = self.scan_result.fs_type
            self.report_info_label.configure(
                text=f"Ready to generate report for {len(self.file_records):,} files "
                     f"(filesystem: {fs}).")
        else:
            self.report_info_label.configure(
                text="No scan data available yet.\nRun a scan first, then generate a report.")

    def generate_report_open(self):
        if not self.scan_result:
            return
        dest = os.path.join(os.path.expanduser("~"), "Documents", "Recovery_Reports")
        path = open_html_report(self.scan_result,
                                self.selected_drive.name or self.selected_drive.letter,
                                self._report_details(), out_dir=dest)
        self._log(f"Report opened: {path}")
        messagebox.showinfo("Report Generated",
                            f"HTML report created:\n{path}")

    def generate_report_save(self):
        if not self.scan_result:
            return
        default = os.path.join(self.recovery_dir_var.get() or os.path.expanduser("~"),
                               f"recovery_report_{time.strftime('%Y%m%d_%H%M%S')}.html")
        path = filedialog.asksaveasfilename(
            defaultextension=".html",
            initialfile=os.path.basename(default),
            initialdir=os.path.dirname(default) or os.path.expanduser("~"),
            filetypes=[("HTML Report", "*.html"), ("All files", "*.*")],
            title="Save HTML Report",
        )
        if not path:
            return
        path = save_html_report(self.scan_result,
                                self.selected_drive.name or self.selected_drive.letter,
                                self._report_details(), path)
        self._log(f"Report saved: {path}")
        messagebox.showinfo("Report Saved", f"Report saved to:\n{path}")

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------
    def run(self):
        self.show_tab("Disks")
        self.mainloop()
