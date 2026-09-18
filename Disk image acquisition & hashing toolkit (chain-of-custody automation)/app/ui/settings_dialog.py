import customtkinter as ctk

from .theme import PANEL2, ACCENT_BTN, ACCENT, MUTED, TEXT, font, BORDER


class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, master, settings, required=False, on_saved=None):
        super().__init__(master)
        self.settings = settings
        self.on_saved = on_saved
        self.result = None
        self.title("Operator Settings")
        self.geometry("460x300")
        self.resizable(False, False)
        self.transient(master)
        if required:
            self.protocol("WM_DELETE_WINDOW", self._block_if_required)

        self.grid_columnconfigure(0, weight=1)
        pad = 20
        ctk.CTkLabel(self, text="Examiner Profile",
                     font=font(17, "bold"), text_color=TEXT, anchor="w").grid(
            row=0, column=0, sticky="w", padx=pad, pady=(20, 2))
        ctk.CTkLabel(self, text="Used to sign every acquisition and chain-of-custody entry.",
                     font=font(12), text_color=MUTED, anchor="w").grid(
            row=1, column=0, sticky="w", padx=pad, pady=(0, 12))

        ctk.CTkLabel(self, text="Investigator / examiner name", font=font(12),
                     text_color=MUTED, anchor="w").grid(row=2, column=0, sticky="w", padx=pad)
        self.name_entry = ctk.CTkEntry(self, fg_color=PANEL2, text_color=TEXT,
                                       border_color=BORDER, font=font(13))
        self.name_entry.grid(row=3, column=0, sticky="ew", padx=pad, pady=(2, 8))

        ctk.CTkLabel(self, text="Role / title", font=font(12),
                     text_color=MUTED, anchor="w").grid(row=4, column=0, sticky="w", padx=pad)
        self.role_entry = ctk.CTkEntry(self, fg_color=PANEL2, text_color=TEXT,
                                       border_color=BORDER, font=font(13))
        self.role_entry.grid(row=5, column=0, sticky="ew", padx=pad, pady=(2, 8))

        hint = ctk.CTkLabel(self, text="", font=font(11), text_color="#ef4444", anchor="w")
        hint.grid(row=6, column=0, sticky="w", padx=pad)
        self.hint = hint

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=7, column=0, sticky="ew", padx=pad, pady=(10, 18))
        btns.grid_columnconfigure(0, weight=1)
        self.save_btn = ctk.CTkButton(btns, text="Save Profile", font=font(13, "bold"),
                                      fg_color=ACCENT_BTN, hover_color="#1b7180",
                                      height=36, command=self._save)
        self.save_btn.grid(row=0, column=1, sticky="e")
        if not required:
            ctk.CTkButton(btns, text="Cancel", font=font(13), fg_color="transparent",
                          border_width=1, border_color=BORDER, text_color=MUTED,
                          height=36, command=self.destroy).grid(row=0, column=0, sticky="e", padx=(0, 8))

        self.name_entry.insert(0, settings.operator)
        self.role_entry.insert(0, settings.role)
        if not required:
            self.bind("<Escape>", lambda _e: self.destroy())
        self.after(80, self._focus)

    def _focus(self):
        self.name_entry.focus_set()

    def _block_if_required(self):
        self.hint.configure(text="An examiner profile is required before first use.")

    def _save(self):
        name = self.name_entry.get().strip()
        role = self.role_entry.get().strip()
        if not name:
            self.hint.configure(text="Please enter the examiner name.")
            return
        if not role:
            self.hint.configure(text="Please enter the examiner role/title.")
            return
        self.settings.operator = name
        self.settings.role = role
        self.destroy()
        if self.on_saved:
            self.on_saved()