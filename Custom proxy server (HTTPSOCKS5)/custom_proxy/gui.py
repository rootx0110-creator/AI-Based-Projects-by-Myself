"""CustomTkinter GUI: sidebar + tabbed dashboard, connections, log, settings."""

from __future__ import annotations

import customtkinter as ctk
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox
import queue
import time

from .config import ProxyConfig
from .constants import (
    APP_NAME,
    APP_VERSION,
    BUFFER_SIZES,
    CONN_HISTORY_MAX,
    MAX_LOG_LINES,
)
from .humanize import fmt_bytes, fmt_rate, fmt_uptime
from .server import ProxyServer

POLL_MS = 100

# ---------------------------------------------------------------- palette
BG = "#0b0f1a"
PANEL = "#121828"
PANEL_2 = "#0e1422"
CARD = "#161d33"
CARD_HOVER = "#1b2440"
BORDER = "#232c4a"
ACCENT = "#4f8cff"
ACCENT_SOFT = "#2b3f6e"
GREEN = "#34d399"
AMBER = "#fbbf24"
RED = "#f87171"
TEXT = "#e6ebf5"
MUTED = "#8a94ad"
LOG_FG = "#9fb4d8"

LOG_COLORS = {
    "INFO": "#7ee2a8",
    "WARNING": "#ffd166",
    "ERROR": "#ff8c8c",
    "DEBUG": "#8a94ad",
}


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*[max(0, min(255, v)) for v in rgb])


def mix(c1: str, c2: str, t: float) -> str:
    a, b = hex_to_rgb(c1), hex_to_rgb(c2)
    return rgb_to_hex(tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3)))


class Sparkline(tk.Canvas):
    """Dual-series (in/out) sparkline on a dark canvas."""

    def __init__(self, master, width=560, height=120, **kw):
        super().__init__(master, width=width, height=height,
                         bg=CARD, highlightthickness=0, **kw)
        self.width = width
        self.height = height
        self.series_in: list[float] = []
        self.series_out: list[float] = []

    def update_series(self, history) -> None:
        self.series_in = [a for a, _ in history]
        self.series_out = [b for _, b in history]
        self.render()

    def render(self) -> None:
        self.delete("all")
        w, h = self.width, self.height
        pad = 6
        # horizontal guide lines
        for i in range(1, 4):
            y = pad + (h - 2 * pad) * i / 4
            self.create_line(pad, y, w - pad, y, fill=BORDER, dash=(2, 4))
        data_in = self.series_in or [0.0]
        peak = max(max(data_in), max(self.series_out or [0.0]), 1.0)
        n = max(len(data_in), len(self.series_out or [0.0]))
        if n < 2:
            return
        step = (w - 2 * pad) / (n - 1)

        # filled area under "out", line for "in"
        data_out_full = self.series_out or [0.0]
        if len(data_out_full) >= 2:
            pts = []
            for i, v in enumerate(data_out_full):
                x = pad + i * step
                y = h - pad - (v / peak) * (h - 2 * pad)
                pts.extend((x, y))
            self.create_line(pts, fill=ACCENT, width=2, smooth=True)
            poly = pts + [pad + (len(data_out_full) - 1) * step, h - pad, pad, h - pad]
            self.create_polygon(poly, fill=mix(CARD, ACCENT, 0.18), outline="")
        if len(data_in) >= 2:
            pts = []
            for i, v in enumerate(data_in):
                x = pad + i * step
                y = h - pad - (v / peak) * (h - 2 * pad)
                pts.extend((x, y))
            self.create_line(pts, fill=GREEN, width=2, smooth=True)
        self.create_text(w - pad, pad, text=f"peak {peak:,.0f} KB/s",
                         anchor="ne", fill=MUTED, font=("Segoe UI", 9))


class StatCard(ctk.CTkFrame):
    def __init__(self, master, title, value_text="--", accent=ACCENT):
        super().__init__(master, fg_color=CARD, corner_radius=14,
                         border_width=1, border_color=BORDER)
        self.accent = accent
        self.grid_columnconfigure(0, weight=1)
        self.title_lbl = ctk.CTkLabel(self, text=title.upper(),
                                      font=("Segoe UI Semibold", 11),
                                      text_color=MUTED, anchor="w")
        self.title_lbl.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 0))
        self.value_lbl = ctk.CTkLabel(self, text=value_text,
                                      font=("Segoe UI Semibold", 22),
                                      text_color=TEXT, anchor="w")
        self.value_lbl.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 12))

    def set_value(self, text: str) -> None:
        self.value_lbl.configure(text=text)


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title(APP_NAME)
        self.geometry("1180x720")
        self.minsize(980, 620)

        cfg, warn = ProxyConfig.load()
        self.cfg = cfg
        self._state = "stopped"
        self.bus: queue.Queue = queue.Queue()
        self.stats = None  # created with server
        self.server = ProxyServer(
            cfg,
            log_fn=lambda level, comp, msg: self.bus.put(("log", level, comp, msg)),
            conn_event_fn=lambda **kw: self.bus.put(("conn", kw)),
        )
        self.stats = self.server.stats
        self.conn_rows: dict[str, dict] = {}
        self.log_lines: list[tuple[str, str, str]] = []  # (level, time, text)
        self.log_dirty = False
        self._uptime_t0 = time.monotonic()
        self._pulse_t = 0.0
        self._closing = False

        if warn:
            self.after(400, lambda: messagebox.showwarning(APP_NAME, warn, parent=self))

        self._build_style()
        self._build_layout()
        self._refresh_static_labels()
        self.after(POLL_MS, self._poll_bus)
        self.after(1000, self._tick_second)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------------------------------------------------------------- layout
    def _build_style(self) -> None:
        self.configure(fg_color=BG)

    def _build_layout(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main()

    def _build_sidebar(self) -> None:
        bar = ctk.CTkFrame(self, width=230, corner_radius=0,
                           fg_color=PANEL_2)
        bar.grid(row=0, column=0, sticky="nsw")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(0, weight=1)

        head = ctk.CTkFrame(bar, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=18, pady=(20, 6))
        ctk.CTkLabel(head, text="◈", font=("Segoe UI", 26),
                     text_color=ACCENT).pack(side="left")
        title_box = ctk.CTkFrame(head, fg_color="transparent")
        title_box.pack(side="left", padx=10)
        ctk.CTkLabel(title_box, text="Custom Proxy",
                     font=("Segoe UI Semibold", 17),
                     text_color=TEXT, anchor="w").pack(anchor="w")
        ctk.CTkLabel(title_box, text=f"v{APP_VERSION}  ·  HTTP + SOCKS5",
                     font=("Segoe UI", 11), text_color=MUTED,
                     anchor="w").pack(anchor="w")

        # Power button
        self.power_btn = ctk.CTkButton(
            bar, text="  START PROXY", height=44, corner_radius=12,
            font=("Segoe UI Semibold", 14), text_color="#08101f",
            fg_color=GREEN, hover_color="#2bbf85", anchor="w",
            command=self.toggle_server,
        )
        self.power_btn.grid(row=1, column=0, sticky="ew", padx=18, pady=(14, 4))

        self.pause_btn = ctk.CTkButton(
            bar, text="⏸  Pause", height=36, corner_radius=10,
            font=("Segoe UI", 13), fg_color=CARD, hover_color=CARD_HOVER,
            text_color=TEXT, anchor="w", state="disabled",
            command=self.toggle_pause,
        )
        self.pause_btn.grid(row=2, column=0, sticky="ew", padx=18, pady=4)

        self.status_card = ctk.CTkFrame(bar, fg_color=CARD, corner_radius=12,
                                        border_width=1, border_color=BORDER)
        self.status_card.grid(row=3, column=0, sticky="ew", padx=18, pady=(18, 8))
        self.status_card.grid_columnconfigure(0, weight=1)
        self.dot = ctk.CTkLabel(self.status_card, text="●", width=14,
                                font=("Segoe UI", 16), text_color=MUTED)
        self.dot.grid(row=0, column=0, sticky="w", padx=(12, 0), pady=(10, 0))
        self.status_lbl = ctk.CTkLabel(self.status_card, text="STOPPED",
                                       font=("Segoe UI Semibold", 14),
                                       text_color=TEXT, anchor="w")
        self.status_lbl.grid(row=0, column=1, sticky="w", padx=8, pady=(10, 0))
        self.uptime_lbl = ctk.CTkLabel(self.status_card, text="uptime —",
                                       font=("Segoe UI", 11), text_color=MUTED,
                                       anchor="w")
        self.uptime_lbl.grid(row=1, column=0, columnspan=2, sticky="w",
                             padx=12, pady=(0, 10))

        # Endpoints
        eps = ctk.CTkFrame(bar, fg_color="transparent")
        eps.grid(row=4, column=0, sticky="ew", padx=18, pady=(6, 8))
        ctk.CTkLabel(eps, text="ENDPOINTS", font=("Segoe UI Semibold", 10),
                     text_color=MUTED, anchor="w").pack(anchor="w", pady=(0, 4))
        self.ep_http_lbl = ctk.CTkLabel(eps, text="HTTP    127.0.0.1:8080",
                                        font=("Consolas", 11), text_color=TEXT,
                                        anchor="w")
        self.ep_http_lbl.pack(anchor="w", pady=1)
        self.ep_socks_lbl = ctk.CTkLabel(eps, text="SOCKS5  127.0.0.1:1080",
                                        font=("Consolas", 11), text_color=TEXT,
                                        anchor="w")
        self.ep_socks_lbl.pack(anchor="w", pady=1)

        tip = ctk.CTkLabel(bar, text="Windows Firewall may prompt\non first start — click Allow.",
                           font=("Segoe UI", 10), text_color=MUTED,
                           justify="left", anchor="w")
        tip.grid(row=5, column=0, sticky="ew", padx=18, pady=(2, 18))

        bar.grid_rowconfigure(6, weight=1)
        foot = ctk.CTkFrame(bar, fg_color="transparent")
        foot.grid(row=7, column=0, sticky="ew", padx=18, pady=(0, 14))
        ctk.CTkLabel(foot, text="Local forward proxy\nasyncio core · no telemetry",
                     font=("Segoe UI", 10), text_color=MUTED,
                     justify="left").pack(anchor="w")

    def _build_main(self) -> None:
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew", padx=16, pady=14)
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)

        # Tab bar (custom, top)
        tabs = ctk.CTkFrame(main, fg_color="transparent")
        tabs.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        for c in range(4):
            tabs.grid_columnconfigure(c, weight=0)
        self.tab_buttons: list[ctk.CTkButton] = []
        self.tabs: list[ctk.CTkFrame] = []
        for i, (name, icon) in enumerate([("Dashboard", "▦"),
                                          ("Connections", "⇄"),
                                          ("Activity Log", "≡"),
                                          ("Settings", "⚙")]):
            b = ctk.CTkButton(
                tabs, text=f" {icon}  {name}", height=34, corner_radius=10,
                font=("Segoe UI Semibold", 13),
                fg_color="transparent", hover_color=CARD_HOVER,
                text_color=MUTED,
                command=lambda idx=i: self.select_tab(idx),
            )
            b.grid(row=0, column=i, padx=(0, 8), sticky="w")
            self.tab_buttons.append(b)

        host = ctk.CTkFrame(main, fg_color=PANEL, corner_radius=16,
                            border_width=1, border_color=BORDER)
        host.grid(row=1, column=0, sticky="nsew")
        host.grid_rowconfigure(0, weight=1)
        host.grid_columnconfigure(0, weight=1)

        pages: list[ctk.CTkFrame] = []
        for i in range(4):
            f = ctk.CTkFrame(host, fg_color="transparent")
            f.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
            pages.append(f)
        self.pages = pages

        self._build_dashboard(pages[0])
        self._build_connections(pages[1])
        self._build_log_page(pages[2])
        self._build_settings(pages[3])
        self.select_tab(0)

    # ---------------------------------------------------------------- pages
    def _build_dashboard(self, page) -> None:
        for c in range(2):
            page.grid_columnconfigure(c, weight=1, uniform="cards")
        outer = ctk.CTkFrame(page, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=18, pady=16)

        # stat cards
        cards = ctk.CTkFrame(outer, fg_color="transparent")
        cards.pack(fill="x")
        cards.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="c")
        self.card_requests = StatCard(cards, "Requests", "--")
        self.card_requests.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.card_active = StatCard(cards, "Active", "--", accent=GREEN)
        self.card_active.grid(row=0, column=1, sticky="ew", padx=8)
        self.card_volume = StatCard(cards, "Transferred", "--", accent=ACCENT)
        self.card_volume.grid(row=0, column=2, sticky="ew", padx=8)
        self.card_errors = StatCard(cards, "Errors", "--", accent=RED)
        self.card_errors.grid(row=0, column=3, sticky="ew", padx=(8, 0))

        # throughput chart
        chart_card = ctk.CTkFrame(outer, fg_color=CARD, corner_radius=14,
                                  border_width=1, border_color=BORDER)
        chart_card.pack(fill="both", expand=True, pady=(12, 0))
        head = ctk.CTkFrame(chart_card, fg_color="transparent")
        head.pack(fill="x", padx=14, pady=(12, 0))
        ctk.CTkLabel(head, text="THROUGHPUT", font=("Segoe UI Semibold", 11),
                     text_color=MUTED, anchor="w").pack(side="left")
        legend = ctk.CTkFrame(head, fg_color="transparent")
        legend.pack(side="right")
        ctk.CTkLabel(legend, text="▬ download", text_color=ACCENT,
                     font=("Segoe UI", 10)).pack(side="left", padx=6)
        ctk.CTkLabel(legend, text="▬ upload", text_color=GREEN,
                     font=("Segoe UI", 10)).pack(side="left", padx=6)
        self.chart = Sparkline(chart_card, width=760, height=170)
        self.chart.pack(fill="both", expand=True, padx=10, pady=(2, 10))
        self.chart.bind("<Configure>", lambda e: self.chart.render())

        # rates row
        rates = ctk.CTkFrame(outer, fg_color="transparent")
        rates.pack(fill="x", pady=(12, 0))
        rates.grid_columnconfigure((0, 1), weight=1, uniform="r")
        self.rate_in_card = StatCard(rates, "Download rate", "--")
        self.rate_in_card.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.rate_out_card = StatCard(rates, "Upload rate", "--")
        self.rate_out_card.grid(row=0, column=1, sticky="ew", padx=(8, 0))

    def _build_connections(self, page) -> None:
        wrap = ctk.CTkFrame(page, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=18, pady=16)
        wrap.grid_rowconfigure(1, weight=1)
        wrap.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(wrap, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.conn_count_lbl = ctk.CTkLabel(
            top, text="Recent connections", font=("Segoe UI Semibold", 13),
            text_color=TEXT)
        self.conn_count_lbl.pack(side="left")
        ctk.CTkButton(top, text="Clear", width=80, height=28, corner_radius=8,
                      fg_color=CARD, hover_color=CARD_HOVER, text_color=MUTED,
                      command=self._clear_conns).pack(side="right")

        table_card = ctk.CTkFrame(wrap, fg_color=CARD, corner_radius=12,
                                  border_width=1, border_color=BORDER)
        table_card.grid(row=1, column=0, sticky="nsew")
        cols = ("time", "proto", "host", "status", "data")
        self.conn_tree = ttk.Treeview(
            table_card, columns=cols, show="headings", height=18,
            style="Conn.Treeview")
        headings = ("Time", "Proto", "Host", "Status", "Data")
        widths = (90, 80, 420, 130, 110)
        for col, txt, w in zip(cols, headings, widths):
            self.conn_tree.heading(col, text=txt)
            self.conn_tree.column(col, width=w, anchor="w", stretch=(col == "host"))
        vsb = ttk.Scrollbar(table_card, orient="vertical",
                            command=self.conn_tree.yview)
        self.conn_tree.configure(yscrollcommand=vsb.set)
        self.conn_tree.pack(side="left", fill="both", expand=True,
                            padx=(10, 0), pady=10)
        vsb.pack(side="right", fill="y", pady=10, padx=(0, 10))
        self.conn_tree.tag_configure("ok", foreground="#7ee2a8")
        self.conn_tree.tag_configure("warn", foreground="#ffd166")
        self.conn_tree.tag_configure("err", foreground="#ff8c8c")

    def _build_log_page(self, page) -> None:
        wrap = ctk.CTkFrame(page, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=18, pady=16)
        wrap.grid_rowconfigure(1, weight=1)
        wrap.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(wrap, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(top, text="Activity log", font=("Segoe UI Semibold", 13),
                     text_color=TEXT).pack(side="left")
        self.autoscroll_var = ctk.BooleanVar(value=self.cfg.autoscroll)
        ctk.CTkSwitch(top, text="Auto-scroll", variable=self.autoscroll_var,
                      progress_color=ACCENT, text_color=MUTED).pack(side="right")
        ctk.CTkButton(top, text="Clear", width=80, height=28, corner_radius=8,
                      fg_color=CARD, hover_color=CARD_HOVER, text_color=MUTED,
                      command=self._clear_log).pack(side="right", padx=8)

        log_card = ctk.CTkFrame(wrap, fg_color="#0a0e18", corner_radius=12,
                                border_width=1, border_color=BORDER)
        log_card.grid(row=1, column=0, sticky="nsew")
        self.log_box = tk.Text(log_card, bg="#0a0e18", fg=LOG_FG, wrap="none",
                               relief="flat", insertbackground=TEXT,
                               selectbackground=ACCENT_SOFT,
                               font=("Consolas", 10), padx=12, pady=10,
                               state="disabled")
        ysb = tk.Scrollbar(log_card, orient="vertical",
                           command=self.log_box.yview)
        self.log_box.configure(yscrollcommand=ysb.set)
        self.log_box.pack(side="left", fill="both", expand=True, padx=(8, 0),
                          pady=8)
        ysb.pack(side="right", fill="y", pady=8, padx=(0, 8))
        for level, color in LOG_COLORS.items():
            self.log_box.tag_configure(level, foreground=color)
        self.log_box.tag_configure("ts", foreground="#5c6784")

    def _build_settings(self, page) -> None:
        wrap = ctk.CTkScrollableFrame(page, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=18, pady=16)
        f = ctk.CTkFrame(wrap, fg_color="transparent")
        f.pack(fill="x", expand=True)
        f.grid_columnconfigure(1, weight=1)

        r = 0

        def section(text, row):
            ctk.CTkLabel(f, text=text, font=("Segoe UI Semibold", 13),
                         text_color=ACCENT, anchor="w").grid(
                row=row, column=0, columnspan=2, sticky="w", pady=(14, 6))

        def entry(row, label, key, width=140, show=""):
            ctk.CTkLabel(f, text=label, text_color=TEXT,
                         font=("Segoe UI", 12), anchor="w").grid(
                row=row, column=0, sticky="w", pady=3, padx=(0, 12))
            e = ctk.CTkEntry(f, width=width, height=30, corner_radius=8,
                             fg_color=CARD, border_color=BORDER,
                             text_color=TEXT, show=show)
            e.grid(row=row, column=1, sticky="w", pady=3)
            e.insert(0, str(getattr(self.cfg, key)))
            setattr(self, f"ent_{key}", e)
            return e

        def switch(row, label, key):
            var = ctk.BooleanVar(value=bool(getattr(self.cfg, key)))
            sw = ctk.CTkSwitch(f, text=label, variable=var,
                               progress_color=ACCENT, text_color=TEXT,
                               font=("Segoe UI", 12))
            sw.grid(row=row, column=0, columnspan=2, sticky="w", pady=3)
            setattr(self, f"sw_{key}", var)
            return sw

        section("Listeners", r); r += 1
        entry(r, "HTTP port", "http_port"); r += 1
        entry(r, "SOCKS5 port", "socks_port"); r += 1
        bind_var = ctk.StringVar(value=self.cfg.bind_mode)
        ctk.CTkLabel(f, text="Bind to", text_color=TEXT,
                     font=("Segoe UI", 12), anchor="w").grid(
            row=r, column=0, sticky="w", pady=3, padx=(0, 12))
        ctk.CTkSegmentedButton(f, values=["localhost", "lan"],
                               variable=bind_var,
                               selected_color=ACCENT,
                               selected_hover_color="#3f78e0",
                               unselected_color=CARD,
                               unselected_hover_color=CARD_HOVER,
                               fg_color=CARD, text_color=TEXT,
                               font=("Segoe UI", 12)).grid(row=r, column=1,
                                                           sticky="w", pady=3)
        self.bind_mode_var = bind_var
        r += 1

        section("Client authentication (optional)", r); r += 1
        switch(r, "Require username / password", "auth_enabled"); r += 1
        entry(r, "Username", "username"); r += 1
        entry(r, "Password", "password", show="•"); r += 1

        section("Upstream proxy chain (optional)", r); r += 1
        switch(r, "Route traffic through another proxy", "upstream_enabled"); r += 1
        up_kind = ctk.StringVar(value=self.cfg.upstream_kind)
        ctk.CTkLabel(f, text="Upstream type", text_color=TEXT,
                     font=("Segoe UI", 12), anchor="w").grid(
            row=r, column=0, sticky="w", pady=3, padx=(0, 12))
        ctk.CTkSegmentedButton(f, values=["http", "socks5"], variable=up_kind,
                               selected_color=ACCENT,
                               selected_hover_color="#3f78e0",
                               unselected_color=CARD,
                               unselected_hover_color=CARD_HOVER,
                               fg_color=CARD, text_color=TEXT,
                               font=("Segoe UI", 12)).grid(row=r, column=1,
                                                           sticky="w", pady=3)
        self.up_kind_var = up_kind
        r += 1
        entry(r, "Upstream host", "upstream_host", width=260); r += 1
        entry(r, "Upstream port", "upstream_port"); r += 1
        entry(r, "Upstream username", "upstream_username"); r += 1
        entry(r, "Upstream password", "upstream_password", show="•"); r += 1

        section("Performance", r); r += 1
        buf_var = ctk.StringVar(
            value=f"{self.cfg.buffer_size // 1024} KB")
        ctk.CTkLabel(f, text="Relay buffer", text_color=TEXT,
                     font=("Segoe UI", 12), anchor="w").grid(
            row=r, column=0, sticky="w", pady=3, padx=(0, 12))
        ctk.CTkSegmentedButton(
            f, values=[f"{b // 1024} KB" for b in BUFFER_SIZES],
            variable=buf_var, selected_color=ACCENT,
            selected_hover_color="#3f78e0", unselected_color=CARD,
            unselected_hover_color=CARD_HOVER, fg_color=CARD,
            text_color=TEXT, font=("Segoe UI", 12)).grid(row=r, column=1,
                                                         sticky="w", pady=3)
        self.buf_var = buf_var
        r += 1
        entry(r, "Connect timeout (s)", "connect_timeout", width=140); r += 1

        section("Appearance", r); r += 1
        mode_var = ctk.StringVar(value=self.cfg.theme_mode)
        ctk.CTkLabel(f, text="Theme", text_color=TEXT,
                     font=("Segoe UI", 12), anchor="w").grid(
            row=r, column=0, sticky="w", pady=3, padx=(0, 12))
        ctk.CTkSegmentedButton(f, values=["dark", "light"], variable=mode_var,
                               selected_color=ACCENT,
                               selected_hover_color="#3f78e0",
                               unselected_color=CARD,
                               unselected_hover_color=CARD_HOVER,
                               fg_color=CARD, text_color=TEXT,
                               font=("Segoe UI", 12),
                               command=self._apply_theme).grid(
            row=r, column=1, sticky="w", pady=3)
        self.mode_var = mode_var
        r += 1

        ctk.CTkButton(f, text="Save settings", height=36, corner_radius=10,
                      font=("Segoe UI Semibold", 13), text_color="#08101f",
                      fg_color=GREEN, hover_color="#2bbf85",
                      command=self._save_settings).grid(
            row=r, column=0, columnspan=2, sticky="w", pady=(18, 4))
        ctk.CTkLabel(f, text="Restarting the proxy applies new listener settings.",
                     font=("Segoe UI", 11), text_color=MUTED,
                     anchor="w").grid(row=r + 1, column=0, columnspan=2,
                                      sticky="w", pady=(4, 0))

    # ---------------------------------------------------------------- tabs
    def select_tab(self, idx: int) -> None:
        for i, b in enumerate(self.tab_buttons):
            active = i == idx
            b.configure(
                fg_color=CARD if active else "transparent",
                text_color=ACCENT if active else MUTED,
                border_width=1 if active else 0,
                border_color=BORDER,
            )
            if active:
                self.pages[i].grid()
            else:
                self.pages[i].grid_remove()

    def _refresh_static_labels(self) -> None:
        bind_ip = "127.0.0.1" if self.cfg.bind_mode == "localhost" else self._lan_ip()
        self.ep_http_lbl.configure(text=f"HTTP    {bind_ip}:{self.cfg.http_port}")
        self.ep_socks_lbl.configure(text=f"SOCKS5  {bind_ip}:{self.cfg.socks_port}")

    @staticmethod
    def _lan_ip() -> str:
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.2)
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "0.0.0.0"

    # ---------------------------------------------------------------- actions
    def toggle_server(self) -> None:
        if self.server.is_running():
            self._stop()
        else:
            self._start()

    def _start(self) -> None:
        err = self.server.start()
        if err:
            messagebox.showerror(APP_NAME, err, parent=self)
            self._set_status("stopped")
            return
        self._set_status("running")
        self.power_btn.configure(text="  STOP PROXY", fg_color=RED,
                                 hover_color="#e05e5e", text_color="#1a0505")
        self.pause_btn.configure(state="normal", text="⏸  Pause")

    def _stop(self) -> None:
        self.server.stop()
        self._set_status("stopped")
        self.power_btn.configure(text="  START PROXY", fg_color=GREEN,
                                 hover_color="#2bbf85", text_color="#08101f")
        self.pause_btn.configure(state="disabled", text="⏸  Pause")

    def toggle_pause(self) -> None:
        if self.server.is_paused():
            self.server.resume()
            self.pause_btn.configure(text="⏸  Pause")
            self._set_status("running")
        else:
            self.server.pause()
            self.pause_btn.configure(text="▶  Resume")
            self._set_status("paused")

    def _set_status(self, state: str) -> None:
        if state == "running":
            self.dot.configure(text_color=GREEN)
            self.status_lbl.configure(text="RUNNING", text_color=GREEN)
        elif state == "paused":
            self.dot.configure(text_color=AMBER)
            self.status_lbl.configure(text="PAUSED", text_color=AMBER)
        else:
            self.dot.configure(text_color=MUTED)
            self.status_lbl.configure(text="STOPPED", text_color=MUTED)
        self._state = state

    # ---------------------------------------------------------------- polling
    def _poll_bus(self) -> None:
        drained_log = False
        try:
            while True:
                kind, *rest = self.bus.get_nowait()
                if kind == "log":
                    level, comp, msg = rest
                    self._append_log(level, comp, msg)
                    drained_log = True
                elif kind == "conn":
                    (info,) = rest
                    self._add_conn_row(info)
        except queue.Empty:
            pass
        self.after(POLL_MS, self._poll_bus)

    def _tick_second(self) -> None:
        snap = self.stats.snapshot()
        self.card_requests.set_value(f"{snap['requests']:,}")
        self.card_active.set_value(f"{snap['active']:,}")
        self.card_volume.set_value(fmt_bytes(snap['bytes_in'] + snap['bytes_out']))
        self.card_errors.set_value(f"{snap['errors']:,}")
        self.rate_in_card.set_value(fmt_rate(snap["rate_in"]))
        self.rate_out_card.set_value(fmt_rate(snap["rate_out"]))
        if self._state == "running":
            self.uptime_lbl.configure(text=f"uptime {fmt_uptime(snap['uptime'])}")
        self.chart.update_series(snap["history"])
        self.after(1000, self._tick_second)

    # ---------------------------------------------------------------- log
    def _append_log(self, level: str, comp: str, msg: str) -> None:
        stamp = time.strftime("%H:%M:%S")
        self.log_lines.append((level, stamp, f"[{comp}] {msg}"))
        if len(self.log_lines) > MAX_LOG_LINES:
            self.log_lines = self.log_lines[-MAX_LOG_LINES:]
            self.log_dirty = True
        self.log_box.configure(state="normal")
        if self.log_dirty:
            self.log_box.delete("1.0", "end")
            self.log_dirty = False
            for lv, ts, text in self.log_lines:
                self.log_box.insert("end", f"{ts} ", ("ts",))
                self.log_box.insert("end", f"{lv:<7} ", (lv,))
                self.log_box.insert("end", text + "\n", (lv,))
        else:
            lv, ts, text = self.log_lines[-1]
            self.log_box.insert("end", f"{ts} ", ("ts",))
            self.log_box.insert("end", f"{lv:<7} ", (lv,))
            self.log_box.insert("end", text + "\n", (lv,))
        self.log_box.configure(state="disabled")
        if self.autoscroll_var.get():
            self.log_box.see("end")

    def _clear_log(self) -> None:
        self.log_lines.clear()
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def _clear_conns(self) -> None:
        for item in self.conn_tree.get_children():
            self.conn_tree.delete(item)

    def _add_conn_row(self, info: dict) -> None:
        stamp = time.strftime("%H:%M:%S")
        status = str(info.get("status", ""))
        tag = "ok"
        if status in ("timeout", "unreachable", "reset", "dns-failure"):
            tag = "err"
        elif status in ("407", "upstream-auth"):
            tag = "warn"
        values = (stamp, info.get("proto", "?"), info.get("host", "?"),
                  status, fmt_bytes(info.get("nbytes", 0)))
        self.conn_tree.insert("", 0, values=values, tags=(tag,))
        children = self.conn_tree.get_children()
        if len(children) > CONN_HISTORY_MAX:
            for item in children[CONN_HISTORY_MAX:]:
                self.conn_tree.delete(item)

    # ---------------------------------------------------------------- misc
    def _apply_theme(self, choice: str) -> None:
        ctk.set_appearance_mode(choice)

    def _save_settings(self) -> None:
        def as_int(entry, default):
            try:
                return int(str(entry.get()).strip())
            except (TypeError, ValueError):
                return default

        def as_float(entry, default):
            try:
                return float(str(entry.get()).strip())
            except (TypeError, ValueError):
                return default

        cfg = ProxyConfig(
            http_port=as_int(self.ent_http_port, self.cfg.http_port),
            socks_port=as_int(self.ent_socks_port, self.cfg.socks_port),
            buffer_size=int(self.buf_var.get().split()[0]) * 1024,
            connect_timeout=as_float(self.ent_connect_timeout,
                                     self.cfg.connect_timeout),
            bind_mode=self.bind_mode_var.get(),
            auth_enabled=bool(self.sw_auth_enabled.get()),
            username=self.ent_username.get().strip(),
            password=self.ent_password.get(),
            upstream_enabled=bool(self.sw_upstream_enabled.get()),
            upstream_kind=self.up_kind_var.get(),
            upstream_host=self.ent_upstream_host.get().strip(),
            upstream_port=as_int(self.ent_upstream_port, self.cfg.upstream_port),
            upstream_username=self.ent_upstream_username.get().strip(),
            upstream_password=self.ent_upstream_password.get(),
            theme_mode=self.mode_var.get(),
            autoscroll=bool(self.autoscroll_var.get()),
        )
        errors = cfg.validate()
        if errors:
            messagebox.showerror(APP_NAME, "\n".join(errors), parent=self)
            return
        self.cfg = cfg
        cfg.save()
        self._refresh_static_labels()
        err = self.server.restart(cfg)
        if err:
            messagebox.showerror(APP_NAME, err, parent=self)
        else:
            messagebox.showinfo(
                APP_NAME, "Settings saved and proxy restarted.",
                parent=self)
        if self.server.is_running():
            self._set_status("running")
        else:
            self._set_status("stopped")

    def _on_close(self) -> None:
        self._closing = True
        try:
            self.server.stop()
        finally:
            self.destroy()


def run_gui() -> None:
    app = App()
    app.mainloop()
