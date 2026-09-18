import os

import customtkinter as ctk
from tkinter import filedialog

from ..core.models import Evidence, format_bytes, utcnow
from .theme import PANEL2, BORDER, ACCENT_BTN, MUTED, TEXT, font


class EvidenceDialog(ctk.CTkToplevel):
    """Register external evidence (media already in custody) on a case."""

    def __init__(self, master, case):
        super().__init__(master)
        self.result = None
        self.case = case
        self.title(f"Register Evidence — {case.case_number}")
        self.geometry("640x560")
        self.resizable(False, False)
        self.transient(master)
        self.grid_columnconfigure(0, weight=1)
        pad = 22

        ctk.CTkLabel(self, text="Register Evidence Item", font=font(17, "bold"),
                     text_color=TEXT, anchor="w").grid(row=0, column=0, sticky="w",
                     padx=pad, pady=(18, 4))
        ctk.CTkLabel(self, text="Describes media already in custody, or staged for acquisition.",
                     font=font(12), text_color=MUTED, anchor="w").grid(row=1, column=0,
                     sticky="w", padx=pad, pady=(0, 10))

        def field(row, label):
            ctk.CTkLabel(self, text=label, font=font(12), text_color=MUTED,
                         anchor="w").grid(row=row, column=0, sticky="w", padx=pad, pady=(4, 1))
            e = ctk.CTkEntry(self, fg_color=PANEL2, border_color=BORDER,
                             text_color=TEXT, font=font(13))
            e.grid(row=row + 1, column=0, sticky="ew", padx=pad, pady=(0, 6))
            return e

        self.label = field(2, "Evidence item label * (e.g. 'Seized Laptop SSD')")
        self.source = field(4, "Source / exhibit tag")

        ctk.CTkLabel(self, text="Source type", font=font(12), text_color=MUTED,
                     anchor="w").grid(row=6, column=0, sticky="w", padx=pad)
        self.stype = ctk.CTkOptionMenu(self, values=["physical_disk", "folder", "image"],
                                       fg_color=PANEL2, button_color=ACCENT_BTN,
                                       button_hover_color="#1b7180", text_color=TEXT,
                                       font=font(13), width=220)
        self.stype.grid(row=7, column=0, sticky="w", padx=pad, pady=(2, 8))

        self.select_btn = ctk.CTkButton(self, text="Select folder / image…", font=font(12),
                                        fg_color="transparent", border_width=1,
                                        border_color=BORDER, text_color="#38bdf8",
                                        height=30, command=self._browse)
        self.select_btn.grid(row=8, column=0, sticky="w", padx=pad, pady=(0, 4))
        self.chosen = ctk.CTkLabel(self, text="", font=font(11), text_color=MUTED,
                                   anchor="w", wraplength=560)
        self.chosen.grid(row=9, column=0, sticky="w", padx=pad)

        self.hint = ctk.CTkLabel(self, text="", font=font(11), text_color="#ef4444", anchor="w")
        self.hint.grid(row=10, column=0, sticky="w", padx=pad, pady=(4, 0))

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=11, column=0, sticky="ew", padx=pad, pady=(12, 18))
        btns.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(btns, text="Cancel", font=font(13), fg_color="transparent",
                      border_width=1, border_color=BORDER, text_color=MUTED, height=36,
                      command=self.destroy).grid(row=0, column=0, sticky="e", padx=(0, 8))
        ctk.CTkButton(btns, text="Register", font=font(13, "bold"), fg_color=ACCENT_BTN,
                      hover_color="#1b7180", height=36, command=self._save).grid(row=0, column=1)

    def _browse(self):
        st = self.stype.get()
        if st == "folder":
            p = filedialog.askdirectory(parent=self)
        else:
            p = filedialog.askopenfilename(parent=self)
        if p:
            self._selected = p
            self.chosen.configure(text=p)

    def _save(self):
        label = self.label.get().strip()
        if not label:
            self.hint.configure(text="Evidence label is required.")
            return
        st = self.stype.get()
        source = self.source.get().strip()
        self.result = Evidence.new(
            case_id=self.case.id,
            item_label=label,
            source_type=st,
            source=source or (getattr(self, "_selected", "") or st),
            target_image="",
            image_format="zip" if st == "folder" else "dd",
            media_info=source,
        )
        self.destroy()