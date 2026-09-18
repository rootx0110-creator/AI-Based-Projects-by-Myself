import time

import customtkinter as ctk

from ..config import APP_VERSION
from .alerts_view import AlertsView
from .dashboard import DashboardView
from .fim_view import FIMView
from .process_view import ProcessView
from .reports_view import ReportsView
from .settings_view import SettingsView
from .theme import ACCENT, BG, CARD_HOVER, MUTED, TEXT, FONT_FAMILY, BORDER


class HIDSUI(ctk.CTk):
    TABS = [
        ("Dashboard", "DashboardView"),
        ("File Integrity", "FIMView"),
        ("Processes", "ProcessView"),
        ("Alerts", "AlertsView"),
        ("Reports", "ReportsView"),
        ("Settings", "SettingsView"),
    ]

    def __init__(self, agent=None):
        super().__init__()
        self.agent = agent
        self.title("HIDS Agent - Host Intrusion Detection")
        self.geometry("1280x800")
        self.minsize(1000, 680)

        self._views = {}
        self._nav_buttons = {}
        self._current = None

        self._build_sidebar()
        self._build_content()
        self._build_statusbar()
        self._show("DashboardView")

        self._tick()

    # ---------------- layout ----------------
    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=210, corner_radius=0, fg_color="#11151c")
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        logo = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo.pack(fill="x", padx=16, pady=(20, 16))
        badge = ctk.CTkFrame(logo, width=34, height=34, corner_radius=10, fg_color=ACCENT)
        badge.pack(side="left", pady=4)
        ctk.CTkLabel(badge, text="H", font=(FONT_FAMILY, 18, "bold"),
                     text_color="#ffffff").pack(expand=True)
        title_box = ctk.CTkFrame(logo, fg_color="transparent")
        title_box.pack(side="left", padx=10)
        ctk.CTkLabel(title_box, text="HIDS Agent", font=(FONT_FAMILY, 14, "bold"),
                     text_color=TEXT).pack(anchor="w")
        ctk.CTkLabel(title_box, text=f"v{APP_VERSION}", font=(FONT_FAMILY, 10),
                     text_color=MUTED).pack(anchor="w")

        nav = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        nav.pack(fill="x", padx=10, pady=8)
        for label, view_name in self.TABS:
            btn = ctk.CTkButton(
                nav, text=label, anchor="w", height=36, corner_radius=8,
                fg_color="transparent", hover_color=CARD_HOVER,
                text_color=MUTED, font=(FONT_FAMILY, 12, "bold"),
                command=lambda n=view_name: self._show(n))
            btn.pack(fill="x", pady=2, padx=2)
            self._nav_buttons[view_name] = btn

        spacer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

        self.agent_pill = ctk.CTkLabel(self.sidebar, text="  AGENT OFFLINE  ",
                                       corner_radius=12, fg_color="#4b2c2c",
                                       text_color="#ffb3b3",
                                       font=(FONT_FAMILY, 10, "bold"))
        self.agent_pill.pack(side="bottom", anchor="w", padx=16, pady=(0, 10))
        ctk.CTkLabel(self.sidebar, text="Security monitoring console",
                     font=(FONT_FAMILY, 9), text_color=MUTED).pack(
            side="bottom", anchor="w", padx=16, pady=(0, 8))

    def _build_content(self):
        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color=BG)
        self.content.pack(side="left", fill="both", expand=True)
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        for label, view_name in self.TABS:
            view = self._create_view(view_name)
            self._views[view_name] = view
            view.grid(row=0, column=0, sticky="nsew")
            view.grid_remove()

    def _create_view(self, name):
        mapping = {
            "DashboardView": DashboardView,
            "FIMView": FIMView,
            "ProcessView": ProcessView,
            "AlertsView": AlertsView,
            "ReportsView": ReportsView,
            "SettingsView": SettingsView,
        }
        return mapping[name](self.content, self.agent)

    def _build_statusbar(self):
        bar = ctk.CTkFrame(self, height=30, corner_radius=0, fg_color="#0b0e13")
        bar.pack(side="bottom", fill="x")
        self.sb_label = ctk.CTkLabel(bar, text="", font=(FONT_FAMILY, 10), text_color=MUTED)
        self.sb_label.pack(side="left", padx=12, pady=4)
        self.sb_right = ctk.CTkLabel(bar, text="", font=(FONT_FAMILY, 10), text_color=MUTED)
        self.sb_right.pack(side="right", padx=12, pady=4)

    # ---------------- navigation ----------------
    def _show(self, name):
        if self._current and self._current in self._views:
            self._views[self._current].grid_remove()
            self._nav_buttons[self._current].configure(fg_color="transparent",
                                                       text_color=MUTED)
        self._current = name
        view = self._views[name]
        view.grid(row=0, column=0, sticky="nsew")
        try:
            view.refresh()
        except Exception:
            pass
        self._nav_buttons[name].configure(fg_color=ACCENT, text_color="#ffffff")

    # ---------------- periodic tick ----------------
    def _tick(self):
        try:
            self._refresh_statusbar()
            if self._current:
                try:
                    self._views[self._current].refresh()
                except Exception:
                    pass
        except Exception:
            pass
        self.after(1000, self._tick)

    def _refresh_statusbar(self):
        agent = self.agent
        dirs = len(agent.watch_dirs())
        try:
            files = sum(agent.storage.baseline_file_count(d) for d in agent.watch_dirs())
        except Exception:
            files = 0
        self.sb_label.configure(
            text=(f"Directories watched: {dirs}   |   Files under monitor: {files}   |   "
                  f"Last FIM scan: {self._ts(agent.last_scan['time'])}   |   "
                  f"Last process snapshot: {self._ts(agent.last_snapshot['time'])}"))
        self.sb_right.configure(text=time.strftime("%H:%M:%S", time.localtime()))

        if agent.running:
            self.agent_pill.configure(text="  AGENT RUNNING  ",
                                      fg_color="#1d3b26", text_color="#9be9a8")
        else:
            self.agent_pill.configure(text="  AGENT OFFLINE  ",
                                      fg_color="#4b2c2c", text_color="#ffb3b3")

    @staticmethod
    def _ts(t):
        if not t:
            return "-"
        import time
        return time.strftime("%H:%M:%S", time.localtime(t))

    def on_close(self):
        self.agent.stop()
        self.destroy()


def run(agent):
    app = HIDSUI(agent)
    app.protocol("WM_DELETE_WINDOW", lambda: app.on_close())
    try:
        app.mainloop()
    except KeyboardInterrupt:
        agent.stop()