import queue
import sys

import customtkinter as ctk

from ..core import Store, CustodySecret
from .theme import (BG, PANEL, PANEL2, BORDER, ACCENT, ACCENT2, MUTED, TEXT,
                    font, ACCENT_BTN)
from .dashboard import DashboardView
from .cases import CasesView
from .acquire import AcquireView
from .verify import VerifyView
from .custody import CustodyView
from .reports import ReportsView

NAV = [
    ("dashboard", "⌂  Dashboard", DashboardView),
    ("cases", "▦  Cases & Evidence", CasesView),
    ("acquire", "⇣  Acquisition", AcquireView),
    ("verify", "✓  Verification", VerifyView),
    ("custody", "⧉  Chain of Custody", CustodyView),
    ("reports", "↧  Reports", ReportsView),
]

SIDEBAR_W = 208


class App:
    def __init__(self):
        self.base_dir = self._base_dir()
        self.data_dir = self._ensure_data_dir()
        self.store = Store(self.data_dir)
        self.secret = CustodySecret(self.data_dir).get()
        self.current: str = None  # key of visible view
        self.active_case_id: str = ""
        self.tasks: dict = {}
        self.ui_queue: queue.Queue = queue.Queue()

        self.views: dict[str, object] = {}

        self.root = ctk.CTk()
        self.root.title("Disk Image Acquisition & Hashing Toolkit — Chain of Custody Automation")
        self.root.geometry("1280x820")
        self.root.minsize(1080, 700)
        self.root.configure(fg_color=BG)
        self._build_sidebar()
        self._build_content()
        self._ensure_operator()
        self._poll_queue()

    # ---------- paths ----------
    def _base_dir(self) -> str:
        if getattr(sys, "frozen", False):
            return sys.executable if False else "."
        return "."

    def _ensure_data_dir(self) -> str:
        import os
        here = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data = os.path.join(here, "data")
        os.makedirs(data, exist_ok=True)
        return data

    # ---------- ui shell ----------
    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self.root, width=SIDEBAR_W, corner_radius=0,
                                    fg_color=PANEL, border_width=0)
        self.sidebar.grid(row=0, column=0, sticky="nsw", rowspan=2)
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_columnconfigure(0, weight=1)

        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=16, pady=(18, 14))
        ctk.CTkLabel(brand, text="▣  FORENSIC", font=font(17, "bold"),
                     text_color=ACCENT, anchor="w").pack(anchor="w")
        ctk.CTkLabel(brand, text="Acquire · Hash · Custody",
                     font=font(10.5), text_color=MUTED, anchor="w").pack(anchor="w")
        ctk.CTkButton(brand, text="Chain of Custody Automation",
                      font=font(8.5), fg_color=ACCENT_BTN, hover_color="#1b7180",
                      width=120, height=18, corner_radius=10).pack(anchor="w", pady=(6, 0))

        ctk.CTkFrame(self.sidebar, height=1, fg_color=BORDER).grid(row=1, column=0, sticky="ew", padx=14)

        self.nav_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.nav_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(12, 0))
        self.nav_frame.grid_columnconfigure(0, weight=1)
        self.nav_buttons = {}
        for i, (key, label, _view) in enumerate(NAV):
            btn = ctk.CTkButton(self.nav_frame, text=label, fg_color="transparent",
                                hover_color=PANEL2, text_color=MUTED,
                                font=font(13), height=38, corner_radius=8,
                                anchor="w", command=lambda k=key: self.show(k))
            btn.grid(row=i, column=0, sticky="ew", pady=1)
            btn.configure(border_width=0)
            self.nav_buttons[key] = btn

        self.status_area = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.status_area.grid(row=3, column=0, sticky="ew", padx=16, pady=(14, 6))
        self.op_label = ctk.CTkLabel(self.status_area, text="Examiner: —",
                                     font=font(11.5), text_color=MUTED, anchor="w")
        self.op_label.pack(anchor="w")
        self.dir_label = ctk.CTkLabel(self.status_area, text="", font=font(10),
                                      text_color=MUTED, anchor="w", wraplength=170)
        self.dir_label.pack(anchor="w")

        ctk.CTkFrame(self.sidebar, height=1, fg_color=BORDER).grid(row=4, column=0, sticky="ew", padx=14)

        settings_btn = ctk.CTkButton(self.sidebar, text="⚙  Operator Settings", fg_color="transparent",
                                     hover_color=PANEL2, text_color=ACCENT2,
                                     font=font(12), height=34, corner_radius=8,
                                     anchor="w", command=self._open_settings)
        settings_btn.grid(row=5, column=0, sticky="ew", padx=10, pady=(10, 0))

        ver = ctk.CTkLabel(self.sidebar, text="v1.0.0  ·  runs fully offline",
                           font=font(9.5), text_color=MUTED, anchor="w")
        ver.grid(row=6, column=0, sticky="ew", padx=18, pady=(14, 12))

    def _build_content(self):
        self.content = ctk.CTkFrame(self.root, fg_color=BG, corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew", padx=(14, 18), pady=(14, 18))
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        self.content_top = ctk.CTkFrame(self.content, fg_color=BG)
        self.content_top.grid(row=0, column=0, sticky="ew")
        self.content_top.grid_columnconfigure(0, weight=1)

        self.head_title = ctk.CTkLabel(self.content_top, text="", font=font(25, "bold"),
                                       text_color=TEXT, anchor="w")
        self.head_title.grid(row=0, column=0, sticky="w")

        bar = ctk.CTkFrame(self.content_top, fg_color="transparent")
        bar.grid(row=0, column=1, sticky="e")
        ctk.CTkLabel(bar, text="Active case:", font=font(12), text_color=MUTED).pack(side="left")
        self.case_combo = ctk.CTkOptionMenu(bar, values=["—"], width=230, height=30,
                                            fg_color=PANEL2, button_color=ACCENT_BTN,
                                            button_hover_color="#1b7180",
                                            text_color=TEXT, font=font(12),
                                            command=self._on_case_selected)
        self.case_combo.pack(side="left", padx=(8, 0))

        ctk.CTkFrame(self.content, height=1, fg_color=BORDER).grid(row=0, column=0, sticky="sew", pady=(10, 10))

        self.view_host = ctk.CTkFrame(self.content, fg_color="transparent")
        self.view_host.grid(row=1, column=0, sticky="nsew")
        self.view_host.grid_columnconfigure(0, weight=1)
        self.view_host.grid_rowconfigure(0, weight=1)

        self.toast = ctk.CTkLabel(self.content, text="", font=font(13), corner_radius=8,
                                  fg_color=PANEL2, text_color=TEXT, width=400)
        self.toast.place(relx=1.0, rely=1.0, x=-12, y=-12, anchor="se")
        self.toast.place_forget()
        self._toast_job = None

    # ---------- operator ----------
    def _ensure_operator(self):
        if self.store.settings.operator and self.store.settings.role:
            self._apply_operator()
            return
        self._open_settings(required=True)

    def _apply_operator(self):
        s = self.store.settings
        self.op_label.configure(text=f"Examiner: {s.operator} ({s.role})")
        self.dir_label.configure(text=f"Workspace: {self.data_dir}")

    def _open_settings(self, required=False):
        from .settings_dialog import SettingsDialog
        dlg = SettingsDialog(self.root, self.store.settings, required, self._on_settings_saved)

    def _on_settings_saved(self):
        self.store.save_settings()
        self._apply_operator()
        self.store.append_custody(
            self.store.settings.operator, self.store.settings.role,
            "OPERATOR_CONFIGURED",
            f"Operator profile set for {self.store.settings.operator}",
            self.secret,
        )
        self.notify("Operator profile saved.")

    # ---------- navigation ----------
    def show(self, key: str):
        if self.current == key and key in self.views:
            return
        for k, _label, _v in NAV:
            self.nav_buttons[k].configure(fg_color="transparent", text_color=MUTED)
        self.nav_buttons[key].configure(fg_color=PANEL2, text_color=ACCENT)
        if key not in self.views:
            _k, label, view_cls = next((n for n in NAV if n[0] == key))
            self.views[key] = view_cls(self.view_host, self)
        else:
            label = next(n[1] for n in NAV if n[0] == key)
        for existing in self.view_host.winfo_children():
            existing.grid_forget()
        view = self.views[key]
        view.grid(row=0, column=0, sticky="nsew")
        self.current = key
        self.head_title.configure(text=label.replace("⌂  ", "").replace("▦  ", "")
                                  .replace("⇣  ", "").replace("✓  ", "")
                                  .replace("⧉  ", "").replace("↧  ", ""))
        view.on_show()

    def _on_case_selected(self, value: str):
        case = None
        if value not in ("—", ""):
            case = next((c for c in self.store.cases if c.display == value), None)
        self.active_case_id = case.id if case else ""
        self.refresh_all()
        if case:
            self.notify(f"Active case: {case.case_number}")

    def refresh_all(self):
        for v in self.views.values():
            try:
                v.refresh()
            except Exception:
                pass

    def refresh_case_combo(self):
        values = [c.display for c in self.store.cases]
        if not values:
            values = ["—"]
        self.case_combo.configure(values=values)
        if self.active_case_id:
            case = self.store.get_case(self.active_case_id)
            if case:
                self.case_combo.set(case.display)
                return
        self.case_combo.set("—")
        self.active_case_id = ""

    # ---------- async task plumbing ----------
    def run_task(self, task_id: str, fn, on_done=None):
        import threading
        holder = {"cancel": threading.Event(), "done": False}
        self.tasks[task_id] = holder

        def worker():
            try:
                result = fn(holder["cancel"])
                self.ui_queue.put({"type": "task_done", "id": task_id,
                                   "result": result, "error": None})
            except Exception as exc:
                self.ui_queue.put({"type": "task_done", "id": task_id,
                                   "result": None, "error": str(exc)})

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def cancel_task(self, task_id: str):
        holder = self.tasks.get(task_id)
        if holder:
            holder["cancel"].set()

    def _poll_queue(self):
        try:
            while True:
                msg = self.ui_queue.get_nowait()
                if msg["type"] == "task_done":
                    holder = self.tasks.pop(msg["id"], None)
                    view = None
                    for v in self.views.values():
                        if hasattr(v, "on_task_done"):
                            try:
                                v.on_task_done(msg["id"], msg["result"], msg["error"])
                            except Exception:
                                pass
                else:
                    self._dispatch_ui_msg(msg)
        except queue.Empty:
            pass
        self.root.after(120, self._poll_queue)

    def _dispatch_ui_msg(self, msg):
        t = msg.get("type")
        if t == "progress":
            view = self.views.get(msg.get("view"))
            if view and hasattr(view, "on_progress"):
                view.on_progress(msg["id"], msg.get("value"), msg.get("text"))

    def emit_progress(self, view_key, task_id, value, text=None):
        self.ui_queue.put({"type": "progress", "view": view_key, "id": task_id,
                           "value": value, "text": text})

    # ---------- toast ----------
    def notify(self, text, color=ACCENT, duration=3200):
        self.toast.configure(text=text, text_color=color)
        self.toast.place(relx=1.0, rely=1.0, x=-12, y=-12, anchor="se")
        self.toast.lift()
        if self._toast_job:
            self.root.after_cancel(self._toast_job)
        self._toast_job = self.root.after(duration, self.toast.place_forget)

    def run(self):
        self.refresh_all()
        self.show("dashboard")
        self.root.mainloop()


def launch():
    app = App()
    app.run()