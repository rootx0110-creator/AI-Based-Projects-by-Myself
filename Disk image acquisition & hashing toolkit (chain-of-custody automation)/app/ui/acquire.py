import os
import time
from tkinter import filedialog

import customtkinter as ctk

from ..core import acquire as acq
from ..core.hasher import hash_file, CancelError
from ..core.models import Evidence, format_bytes
from .base import BaseView
from .theme import (PANEL2, PANEL, BORDER, ACCENT, ACCENT2, GOOD, BAD, MUTED,
                    TEXT, font, ACCENT_BTN)
from .widgets import SectionCard
from datetime import datetime

HASH_NAMES = {"md5": "MD5", "sha1": "SHA-1", "sha256": "SHA-256"}


class AcquireView(BaseView):
    key = "acquire"
    title = "Acquisition"
    subtitle = "Create a forensic image with live integrity hashing in a single pass"

    def __init__(self, master, app):
        super().__init__(master, app)
        self._cancel = None
        self._busy = False

        body = self.body
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(5, weight=1)

        col = ctk.CTkFrame(body, fg_color="transparent")
        col.grid(row=0, column=0, columnspan=2, sticky="ew")
        col.grid_columnconfigure(0, weight=1)
        col.grid_columnconfigure(1, weight=1)
        col.grid_columnconfigure(2, weight=1)

        self.src_card = SectionCard(col, "1 · Source")
        self.src_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        src_body = self.src_card.body
        src_body.grid_columnconfigure(0, weight=1)

        self.src_mode = ctk.CTkSegmentedButton(src_body, values=["Physical Disk", "Folder", "Existing Image"],
                                               font=font(12), fg_color=PANEL2,
                                               selected_color=ACCENT_BTN,
                                               selected_hover_color="#1b7180",
                                               text_color=MUTED, command=self._mode_changed)
        self.src_mode.set("Physical Disk")
        self.src_mode.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        self.disk_menu = ctk.CTkOptionMenu(src_body, values=["Refresh disks…"], width=330,
                                           fg_color=PANEL2, button_color=ACCENT_BTN,
                                           button_hover_color="#1b7180", text_color=TEXT,
                                           font=font(12))
        self.disk_menu.grid(row=1, column=0, sticky="w")
        self.disk_note = ctk.CTkLabel(src_body, text="", font=font(10.5), text_color=MUTED,
                                      anchor="w", wraplength=340)
        self.disk_note.grid(row=2, column=0, sticky="w", pady=(4, 0))
        self.disk_refresh = ctk.CTkButton(src_body, text="↻  Refresh disk list", font=font(11),
                                          fg_color="transparent", border_width=1,
                                          border_color=BORDER, text_color=ACCENT2,
                                          height=26, command=self._load_disks)
        self.disk_refresh.grid(row=3, column=0, sticky="w", pady=(6, 0))
        self._load_disks()

        self.folder_frame = ctk.CTkFrame(src_body, fg_color="transparent")
        self.folder_frame.grid_columnconfigure(0, weight=1)
        self.folder_btn = ctk.CTkButton(self.folder_frame, text="Choose folder…", font=font(12),
                                        fg_color="transparent", border_width=1,
                                        border_color=BORDER, text_color=ACCENT2, height=30,
                                        command=self._pick_folder)
        self.folder_btn.grid(row=0, column=0, sticky="w")
        self.folder_path = ctk.CTkLabel(self.folder_frame, text="", font=font(10.5),
                                        text_color=MUTED, anchor="w", wraplength=400)
        self.folder_path.grid(row=1, column=0, sticky="w", pady=(4, 0))

        self.file_frame = ctk.CTkFrame(src_body, fg_color="transparent")
        self.file_frame.grid_columnconfigure(0, weight=1)
        self.file_btn = ctk.CTkButton(self.file_frame, text="Choose image file…", font=font(12),
                                      fg_color="transparent", border_width=1,
                                      border_color=BORDER, text_color=ACCENT2, height=30,
                                      command=self._pick_image)
        self.file_btn.grid(row=0, column=0, sticky="w")
        self.file_path = ctk.CTkLabel(self.file_frame, text="", font=font(10.5),
                                      text_color=MUTED, anchor="w", wraplength=400)
        self.file_path.grid(row=1, column=0, sticky="w", pady=(4, 0))

        self.label_card = SectionCard(col, "2 · Evidence Label")
        self.label_card.grid(row=0, column=1, sticky="nsew", padx=8)
        lbl = self.label_card.body
        lbl.grid_columnconfigure(0, weight=1)
        self.item_entry = ctk.CTkEntry(lbl, placeholder_text="e.g. Seized PC System Drive",
                                       fg_color=PANEL2, border_color=BORDER,
                                       text_color=TEXT, font=font(13))
        self.item_entry.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.alg_vars = {}
        self.alg_frame = ctk.CTkFrame(lbl, fg_color="transparent")
        self.alg_frame.grid(row=1, column=0, sticky="w")
        for i, alg in enumerate(("md5", "sha1", "sha256")):
            var = ctk.BooleanVar(value=True)
            ctk.CTkCheckBox(self.alg_frame, text=HASH_NAMES[alg], variable=var,
                             font=font(12), text_color=TEXT, fg_color=ACCENT_BTN,
                             hover_color="#1b7180", border_color=BORDER).grid(
                row=0, column=i, padx=(0, 14))
            self.alg_vars[alg] = var
        self.case_hint = ctk.CTkLabel(lbl, text="", font=font(11), text_color="#f59e0b",
                                      anchor="w", wraplength=300)
        self.case_hint.grid(row=2, column=0, sticky="w", pady=(8, 0))

        self.out_card = SectionCard(col, "3 · Target Image")
        self.out_card.grid(row=0, column=2, sticky="nsew", padx=(8, 0))
        out = self.out_card.body
        out.grid_columnconfigure(0, weight=1)
        self.out_dir = ctk.CTkEntry(out, placeholder_text="Output folder", fg_color=PANEL2,
                                    border_color=BORDER, text_color=TEXT, font=font(12))
        self.out_dir.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        self.out_name = ctk.CTkEntry(out, placeholder_text="Image file name", fg_color=PANEL2,
                                     border_color=BORDER, text_color=TEXT, font=font(12))
        self.out_name.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        btn_row = ctk.CTkFrame(out, fg_color="transparent")
        btn_row.grid(row=2, column=0, columnspan=2, sticky="ew")
        ctk.CTkButton(btn_row, text="Browse…", font=font(11), fg_color="transparent",
                      border_width=1, border_color=BORDER, text_color=ACCENT2, height=26,
                      command=self._pick_outdir).pack(side="left")
        self.ext_label = ctk.CTkLabel(btn_row, text="extension: .img", font=font(11),
                                      text_color=MUTED)
        self.ext_label.pack(side="right")
        self.net_label = ctk.CTkLabel(out, text="", font=font(10.5), text_color=MUTED,
                                      anchor="w", wraplength=320)
        self.net_label.grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))
        self.out_dir.insert(0, os.path.join(self.app.data_dir, "images"))

        self.ctl_card = SectionCard(body, "4 · Execute")
        self.ctl_card.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ctl = self.ctl_card.body
        ctl.grid_columnconfigure(1, weight=1)
        self.start_btn = ctk.CTkButton(ctl, text="▶  Start Acquisition", font=font(14, "bold"),
                                       fg_color=ACCENT_BTN, hover_color="#1b7180", height=40,
                                       width=190, command=self._start)
        self.start_btn.grid(row=0, column=0, sticky="w")
        self.stop_btn = ctk.CTkButton(ctl, text="■  Stop", font=font(13, "bold"),
                                      fg_color="#7f1d1d", hover_color="#991b1b",
                                      height=40, width=110, state="disabled", command=self._stop)
        self.stop_btn.grid(row=0, column=2, sticky="e", padx=(10, 0))
        self.status_label = ctk.CTkLabel(ctl, text="Idle", font=font(12), text_color=MUTED,
                                         anchor="w")
        self.status_label.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        self.prog = ctk.CTkProgressBar(ctl, fg_color=PANEL2, progress_color=ACCENT, height=12)
        self.prog.set(0)
        self.prog.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(6, 0))

        self.result_frame = ctk.CTkFrame(body, fg_color="transparent")
        self.result_frame.grid(row=5, column=0, columnspan=2, sticky="nsew", pady=(12, 0))
        self.result_frame.grid_columnconfigure(0, weight=1)
        self.result_card = SectionCard(self.result_frame, "Live Hashing / Result")
        self.result_card.grid(row=0, column=0, sticky="nsew")
        res = self.result_card.body
        res.grid_columnconfigure(1, weight=1)
        self.res_labels = {}
        self.res_value = ctk.CTkLabel(res, text="", font=font(11), text_color=MUTED,
                                      anchor="w", justify="left")
        self.res_value.grid(row=0, column=0, sticky="w")

        self._mode_changed("Physical Disk")

    # ---------- source controls ----------
    def _mode_changed(self, mode):
        is_disk = mode == "Physical Disk"
        is_folder = mode == "Folder"
        is_file = mode == "Existing Image"
        self.disk_menu.grid() if is_disk else self.disk_menu.grid_remove()
        self.disk_note.grid() if is_disk else self.disk_note.grid_remove()
        self.disk_refresh.grid() if is_disk else self.disk_refresh.grid_remove()
        self.folder_frame.grid(row=1, column=0, sticky="ew", pady=(6, 0)) if is_folder else self.folder_frame.grid_remove()
        self.file_frame.grid(row=1, column=0, sticky="ew", pady=(6, 0)) if is_file else self.file_frame.grid_remove()
        self.ext_label.configure(text="extension: .img" if is_disk else ("extension: .zip" if is_folder else "extension: —"))
        if is_file:
            self.status_label.configure(text="Existing image will be hashed and registered (no new file created).")
        else:
            self.status_label.configure(text="Idle")

    def _load_disks(self):
        self.disk_menu.configure(values=["Loading…"])
        self.disk_menu.set("Loading…")
        try:
            disks = acq.list_physical_drives()
        except Exception:
            disks = []
        self._disks = disks
        if not disks:
            self.disk_menu.configure(values=["No disks detected"])
            self.disk_menu.set("No disks detected")
            self.disk_note.configure(text="Run as Administrator for raw physical-drive access. Listing only detected clock drives.")
            return
        labels = []
        for d in disks:
            size = format_bytes(d["size"])
            labels.append(f"Disk {d['index']} — {d['model'][:38]} ({size})")
        self.disk_menu.configure(values=labels)
        self.disk_menu.set(labels[0])
        d = disks[0]
        self.disk_note.configure(
            text=f"{d['model']} · Serial {d['serial'] or '—'}\n"
                 f"{d['media_type'] or ''} {d['interface'] or ''} · Administrator rights required for imaging.")

    def _selected_disk(self):
        if not getattr(self, "_disks", None):
            return None
        val = self.disk_menu.get()
        for i, d in enumerate(self._disks):
            if val.startswith(f"Disk {d['index']} —"):
                return d
        return None

    def _pick_folder(self):
        p = filedialog.askdirectory(title="Select logical source folder")
        if p:
            self.folder_path.configure(text=p)

    def _pick_image(self):
        p = filedialog.askopenfilename(title="Select existing image file",
                                       filetypes=[("Images", "*.img *.dd *.raw *.zip *.E01 *.e01"), ("All", "*.*")])
        if p:
            self.file_path.configure(text=p)

    def _pick_outdir(self):
        p = filedialog.askdirectory(title="Select output folder")
        if p:
            self.out_dir.delete(0, "end")
            self.out_dir.insert(0, p)

    def _update_name(self):
        if not self.out_name.get().strip():
            case = self.app.store.get_case(self.app.active_case_id)
            prefix = (case.case_number.replace(" ", "_") if case else "Case")
            ext = "img" if self.src_mode.get() == "Physical Disk" else ("zip" if self.src_mode.get() == "Folder" else "img")
            name = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
            self.out_name.delete(0, "end")
            self.out_name.insert(0, name)

    # ---------- execution ----------
    def _collect_config(self):
        case = self.app.store.get_case(self.app.active_case_id)
        if not case:
            self.case_hint.configure(text="Additional identifier recorded with the evidence is the case. Select/create a case first.")
            self.app.notify("Set an active case first (combo top-right).", BAD)
            return None
        mode = self.src_mode.get()
        label = self.item_entry.get().strip()
        if not label:
            self.app.notify("Enter an evidence item label.", BAD)
            return None
        algs = tuple(a for a, v in self.alg_vars.items() if v.get())
        if not algs:
            self.app.notify("Select at least one hash algorithm.", BAD)
            return None
        out_dir = self.out_dir.get().strip() or os.path.join(self.app.data_dir, "images")
        name = self.out_name.get().strip()
        return {"case": case, "mode": mode, "label": label, "algs": algs,
                "out_dir": out_dir, "name": name}

    def _start(self):
        if self._busy:
            return
        cfg = self._collect_config()
        if not cfg:
            return
        self._update_name()
        cfg["name"] = self.out_name.get().strip()
        mode = cfg["mode"]

        case = cfg["case"]
        if mode == "Physical Disk":
            disk = self._selected_disk()
            if not disk:
                self.app.notify("Select a physical disk first.", BAD)
                return
            target = os.path.join(cfg["out_dir"], cfg["name"] + ("" if cfg["name"].endswith(".img") else ".img"))
            src_desc = f"PhysicalDrive{disk['index']}"
            media = f"{disk['model']} — Serial {disk['serial'] or '?'} — {format_bytes(disk['size'])}"
            os.makedirs(cfg["out_dir"], exist_ok=True)
        elif mode == "Folder":
            folder = self.folder_path.cget("text")
            if not folder or not os.path.isdir(folder):
                self.app.notify("Choose a valid folder first.", BAD)
                return
            target = os.path.join(cfg["out_dir"], cfg["name"] + ("" if cfg["name"].endswith(".zip") else ".zip"))
            os.makedirs(cfg["out_dir"], exist_ok=True)
            src_desc, media = folder, "Logical folder (STORE-mode archive)"
        else:
            img = self.file_path.cget("text")
            if not img or not os.path.isfile(img):
                self.app.notify("Choose an existing image file first.", BAD)
                return
            target, src_desc = img, img
            media = "Existing image — hash-only registration"

        self._busy = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.res_labels = {}
        self.prog.set(0)
        self.status_label.configure(text=f"Starting {mode}…", text_color=ACCENT2)
        self._task_id = f"acq_{int(time.time())}"
        self._cfg = cfg | {"target": target, "src_desc": src_desc, "media": media, "mode": mode}
        self.app.run_task(self._task_id, self._worker)

    def _worker(self, cancel):
        cfg = self._cfg
        algs = cfg["algs"]
        mode = cfg["mode"]

        def prog(frac, text=None):
            self.app.emit_progress("acquire", self._task_id, frac if frac is not None else 0.0,
                                   text=text)

        if mode == "Physical Disk":
            disk = self._selected_disk()
            res = acq.acquire_physical_disk(disk["index"], cfg["target"], disk["serial"],
                                            disk["model"], disk["size"], algs, prog, cancel)
        elif mode == "Folder":
            res = acq.acquire_folder(cfg["src_desc"], cfg["target"], algs, prog, cancel)
        else:
            res, size = None, None
            hashes, total = hash_file(cfg["target"], algs, prog, cancel)
            res = acq.DiskAcquisitionResult(hashes=hashes, size_bytes=total,
                                            media_info="Existing image (hashed)", files_count=1)
        return res, cfg

    def on_progress(self, task_id, value, text):
        if task_id != getattr(self, "_task_id", ""):
            return
        self.prog.set(value if value is not None else 0)
        if text:
            self.status_label.configure(text=text, text_color=ACCENT2)

    def on_task_done(self, task_id, result, error):
        if task_id != getattr(self, "_task_id", ""):
            return
        self._busy = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.app.cancel_task(task_id)
        if error:
            self.prog.set(0)
            self.status_label.configure(text=f"Failed: {error}", text_color=BAD)
            self.app.notify("Acquisition failed.", BAD)
            self.app.store.append_custody(
                self.app.store.settings.operator, self.app.store.settings.role,
                "ACQUISITION_FAILED",
                f"{self._cfg['label']}: {error}", self.app.secret)
            return
        res, cfg = result
        self.prog.set(1)
        self.status_label.configure(text="Complete — image acquired and hashed.", text_color=GOOD)

        ev = Evidence.new(
            case_id=cfg["case"].id,
            item_label=cfg["label"],
            source_type="physical_disk" if cfg["mode"] == "Physical Disk" else ("folder" if cfg["mode"] == "Folder" else "image"),
            source=cfg["src_desc"],
            target_image=cfg["target"],
            image_format="dd" if cfg["mode"] == "Physical Disk" else ("zip" if cfg["mode"] == "Folder" else "dd"),
            media_info=cfg["media"],
        )
        ev.hashes = {k: v for k, v in res.hashes.items()}
        ev.size_bytes = res.size_bytes
        ev.acquired_by = f"{self.app.store.settings.operator} ({self.app.store.settings.role})"
        ev.status = "Acquired"
        self.app.store.add_evidence(ev)
        self.app.store.append_custody(
            self.app.store.settings.operator, self.app.store.settings.role,
            "ACQUISITION_COMPLETED",
            f"{cfg['label']} — {cfg['mode']} · SHA-256 {res.hashes.get('sha256', '—')[:20]}… · {format_bytes(res.size_bytes)}",
            self.app.secret)

        res_body = self.result_card.body
        res_body.grid_columnconfigure(1, weight=1)
        self.res_summary = ctk.CTkLabel(res_body, text="", font=font(12), text_color=GOOD,
                                        anchor="w", justify="left")
        self.res_summary.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
        self.res_summary.configure(
            text=f"Evidence: {ev.item_label}\nImage: {cfg['target']}\nMedia: {cfg['media']}\nSize: {format_bytes(res.size_bytes)}")
        row = 1
        for alg in cfg["algs"]:
            self.res_value = ctk.CTkLabel(res_body, text=HASH_NAMES[alg], font=font(12, "bold"),
                                          text_color=ACCENT2, anchor="w")
            self.res_value.grid(row=row, column=0, sticky="w", pady=1)
            self.res_hash = ctk.CTkLabel(res_body, text=res.hashes.get(alg, ""), font=font(12, "bold"),
                                         text_color=GOOD, anchor="w")
            self.res_hash.grid(row=row, column=1, sticky="w", padx=(8, 0), pady=1)
            row += 1
        self.app.notify("Acquisition complete — hashes recorded.")
        self.app.refresh_all()

    def _stop(self):
        if self._busy:
            self.app.cancel_task(getattr(self, "_task_id", ""))
            self.status_label.configure(text="Cancelling…", text_color="#f59e0b")
        self.item_entry.delete(0, "end")