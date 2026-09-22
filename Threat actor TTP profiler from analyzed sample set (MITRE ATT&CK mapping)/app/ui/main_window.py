"""Main application window: sidebar navigation + page host."""

from __future__ import annotations

import os
import sys

import customtkinter as ctk

from . import theme
from .worker import TaskRunner


def resource_path(rel: str) -> str:
    """Locate a project data file when frozen by PyInstaller or run from source."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        path = os.path.join(base, rel)
        if os.path.exists(path):
            return path
    path = os.path.abspath(os.environ.get("APP_DATA_DIR", ""))
    return os.path.abspath(
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            rel,
        )
    )


class MainWindow(ctk.CTk):
    def __init__(self, workbench) -> None:
        super().__init__()
        self.workbench = workbench
        self.runner = TaskRunner()
        self.pages = {}
        self.current_page = None

        ctk.set_appearance_mode("dark")
        self.title("Threat Actor TTP Profiler — MITRE ATT&CK Mapping")
        # CustomTkinter multiplies the requested geometry by a window-scaling
        # factor (~1.25 on a 125% display) applied asynchronously by the window
        # manager, so fixed sizes could open larger than the screen and cut off
        # tab content. Clamp the window to the screen in Tk's own coordinate
        # space (which maps 1:1 onto the physical screen), then fine-tune the
        # size once the window is actually mapped (see _fit_to_screen).
        self.minsize(800, 520)
        _sw, _sh = self.winfo_screenwidth(), self.winfo_screenheight()
        try:
            self.maxsize(_sw, _sh)  # hard clamp: window can never exceed the screen
        except Exception:  # noqa: BLE001
            pass
        self._fit_target = (min(1360, _sw - 32), min(790, _sh - 72), _sw, _sh)
        _w, _h = self._fit_target[0], self._fit_target[1]
        self.geometry("%dx%d+%d+%d" % (
            _w, _h, max(0, (_sw - _w) // 2), max(0, (_sh - _h) // 2 - 8)))
        self.after(80, self._fit_to_screen)
        self.configure(fg_color=theme.BG)

        self._build_layout()
        self._build_sidebar()
        self._build_pages()
        self.show_page("dashboard")

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(150, self._poll)

    def _fit_to_screen(self) -> None:
        """Fine-tune window size after mapping, dividing out any applied scale."""
        try:
            _w, _h, _sw, _sh = self._fit_target
            fw = self.winfo_width() / float(_w)
            fh = self.winfo_height() / float(_h)
            if abs(fw - 1.0) > 0.02 or abs(fh - 1.0) > 0.02:
                _cw = min(_sw, max(800, round(_w / fw)))
                _ch = min(_sh, max(520, round(_h / fh)))
                self.geometry("%dx%d+%d+%d" % (
                    _cw, _ch, max(0, (_sw - _cw) // 2), max(0, (_sh - _ch) // 2 - 8)))
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------
    def _build_layout(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=theme.SIDEBAR_WIDTH, corner_radius=0, fg_color=theme.SIDEBAR)
        self.sidebar.grid(row=0, column=0, sticky="nsw", padx=(0, 0), pady=0)
        self.sidebar.grid_propagate(False)

        self.content = ctk.CTkFrame(self, fg_color=theme.BG, corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        self.statusbar = ctk.CTkLabel(
            self, text="Ready", anchor="w", height=30, fg_color=theme.FRAME,
            text_color=theme.TEXT_MUTED, font=ctk.CTkFont(theme.FONT, theme.FS_TINY),
        )
        self.statusbar.grid(row=1, column=1, sticky="sew")

    def _build_sidebar(self) -> None:
        self.sidebar.grid_columnconfigure(0, weight=1)
        logo = ctk.CTkLabel(
            self.sidebar, text="TTP  PROFILER",
            font=ctk.CTkFont(theme.FONT, theme.FS_H2 + 2, "bold"), text_color=theme.TEXT,
        )
        logo.grid(row=0, column=0, padx=18, pady=(22, 4), sticky="w")

        sub = ctk.CTkLabel(
            self.sidebar, text="MITRE ATT&CK Mapping",
            font=ctk.CTkFont(theme.FONT, theme.FS_TINY), text_color=theme.TEXT_MUTED,
        )
        sub.grid(row=1, column=0, padx=18, pady=(0, 18), sticky="w")

        nav = [
            ("dashboard", "  Dashboard"),
            ("samples", "  Sample Analysis"),
            ("attack", "  MITRE ATT&CK"),
            ("actors", "  Threat Actor"),
            ("navigator", "  ATT&CK Navigator"),
            ("reports", "  Reports"),
            ("settings", "  Settings"),
        ]
        self.nav_buttons = {}
        row = 2
        for key, label in nav:
            btn = ctk.CTkButton(
                self.sidebar, text=label, anchor="w", height=42,
                font=ctk.CTkFont(theme.FONT, theme.FS_BODY), corner_radius=8,
                fg_color="transparent", text_color=theme.TEXT,
                hover_color=theme.FRAME_2,
                command=lambda k=key: self.show_page(k),
            )
            btn.grid(row=row, column=0, padx=12, pady=3, sticky="ew")
            self.nav_buttons[key] = btn
            row += 1

        version = "v1.0.0"
        build = ctk.CTkLabel(
            self.sidebar, text="%s\nAuthorized analysis tool\nCFMT / IOC / TTP workflow" % version,
            font=ctk.CTkFont(theme.FONT, theme.FS_TINY), text_color=theme.TEXT_MUTED, justify="left",
        )
        build.grid(row=row + 4, column=0, padx=18, pady=(30, 8), sticky="sw")
        self.sidebar.grid_rowconfigure(row + 4, weight=1)

    def _build_pages(self) -> None:
        from .pages.dashboard import DashboardPage
        from .pages.samples import SamplesPage
        from .pages.attack_page import AttackPage
        from .pages.actor_profile import ActorPage
        from .pages.navigator import NavigatorPage
        from .pages.reports import ReportsPage
        from .pages.settings import SettingsPage

        for key in ("dashboard", "samples", "attack", "actors", "navigator", "reports", "settings"):
            frame = ctk.CTkFrame(self.content, fg_color=theme.BG, corner_radius=0)
            # Pages are gridded on demand in show_page(). Gridding every page up front
            # stacks them in one cell with the last page (Settings) on top, which made
            # Settings visible at startup and swallowed nav clicks.
            frame.grid_columnconfigure(0, weight=1)
            frame.grid_rowconfigure(0, weight=1)
            self.pages[key] = frame

        self.page_objects = {
            "dashboard": DashboardPage(self, self.pages["dashboard"]),
            "samples": SamplesPage(self, self.pages["samples"]),
            "attack": AttackPage(self, self.pages["attack"]),
            "actors": ActorPage(self, self.pages["actors"]),
            "navigator": NavigatorPage(self, self.pages["navigator"]),
            "reports": ReportsPage(self, self.pages["reports"]),
            "settings": SettingsPage(self, self.pages["settings"]),
        }
        for obj in self.page_objects.values():
            obj._build()

    # ------------------------------------------------------------------
    def show_page(self, key: str) -> None:
        if self.current_page:
            self.pages[self.current_page].grid_remove()
        self.current_page = key
        # sticky + fill: pages are gridded for the first time here (they are not
        # pre-gridded in _build_pages), so the stretch options must be given —
        # a bare .grid() leaves the page centered at its natural size.
        self.pages[key].grid(row=0, column=0, sticky="nsew")
        self.pages[key].grid_propagate(False)
        self.pages[key].lift()
        for nav_key, btn in self.nav_buttons.items():
            active = nav_key == key
            btn.configure(
                fg_color=theme.SIDEBAR_ACTIVE if active else "transparent",
                text_color="#ffffff" if active else theme.TEXT,
            )
        try:
            self.page_objects[key].on_show()
        except Exception as exc:  # noqa: BLE001
            self._report_error("on_show(%s)" % key, exc)

    def refresh_all(self) -> None:
        for obj in self.page_objects.values():
            try:
                obj.refresh()
            except Exception as exc:  # noqa: BLE001
                self._report_error("refresh(%s)" % type(obj).__name__, exc)

    def _report_error(self, where: str, exc: Exception) -> None:
        try:
            with open(self._log_path(), "a", encoding="utf-8") as fh:
                fh.write("[ui] %s: %r\n" % (where, exc))
        except Exception:  # noqa: BLE001
            pass
        self.set_status("Error in %s: %s" % (where, exc))

    @staticmethod
    def _log_path() -> str:
        import os  # noqa: PLC0415

        base = os.environ.get("LOCALAPPDATA") or os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base, "ThreatActorTTPProfiler", "startup.log")

    def set_status(self, text: str) -> None:
        self.statusbar.configure(text="  " + text)

    # ------------------------------------------------------------------
    def _poll(self) -> None:
        try:
            if self.runner.pump():
                self.runner.busy = False
                self.refresh_all()
                self.set_status("Done.")
        except Exception as exc:  # noqa: BLE001
            self.set_status("Error: %s" % exc)
        self.after(150, self._poll)

    def run_analysis(self) -> None:
        self.runner.submit(
            lambda: (self.workbench.reanalyze(), "ok"),
            on_done=self._analysis_done,
            on_error=self._analysis_error,
        )
        self.set_status("Analyzing %d samples..." % len(self.workbench.samples))

    def _analysis_done(self, _res=None) -> None:
        self.set_status("Analysis complete: %d techniques, %d actors." % (
            len(self.workbench.techniques), len(self.workbench.actors)))
        if len(self.workbench.techniques) == 0:
            self.set_status("Analysis complete — no techniques detected (check sample indicators).")

    def _analysis_error(self, exc: Exception) -> None:
        self.set_status("Analysis error: %s" % exc)

    def _on_close(self) -> None:
        self.destroy()