"""Main window shell for SubnetPlanner."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path

import tkinter as tk
from tkinter import ttk

from . import theme as T
from .pages import ReportPage, SubnetPage, VlsmPage
from .widgets import setup_style

APP_VERSION = "1.0.0"
APP_NAME = "SubnetPlanner"

SETTINGS_DIR = Path.home() / ".subnetplanner"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"

# 64x64 app icon (embedded so the one-file exe has no file to find)
_ICON_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAQAAAAEACAYAAABccqhmAAAJgElEQVR4nO3dS49cRxUA4Fum8URiAcJmBkvseYisAhHJKhskFoi/QBRDjASIJOzCY7qV2BISLFgADrEj9ohNxAKJf8DvYAHskfDwGDTTGBkzr+6+99apOt8ntaJklL7VdarOrVP39u3y4YPPDI04rt0A2EAZGrAYYjLZad1xC0lhEaRNJjwZHD/17yV7AjDxyez4P/8smUoAkx7OnxOzJoPFUGY7nokPwVYFc5QAJj4ETQTXpnxzkx9in0CnWgE460MDq4EpEoDJD9M4mVujTtjFyPPf5IeGksBYKwATHxosCcZIACY/NLoa2PUqgMkPdR3XuhHI5IfGVwLblgAmP3SQBLYpAUx+iOl46hWAyQ8drQRqfx0YqGixwR6gsz90tgq46grA5IcOk8BVEoDJD50mgam/DgwEdtkKwNkfOl4FXHQnoMkPnScBJQAkdl4J4OwPCVYBbgSCxM7aA3D2hySrAHsAkJgSABJ7OgFY/kOiMkAJAIk9uQno7A/JVgH2ACAxJQAkZgUAiS3KuhRQ/0PCfYCxfxsQaIgSABKTACAxVwEg+Y1ANgAhp2MlACSmBIDErAAgMQkAEnMjECRmBQCJSQCQmKsAkJgVACR20W8DAp2zAoDE7AFAYo+fCAQkZA8AElMCQGI2ASExCQASUwJAYjYBITElACSmBIDErAAgMQkAEvNIMEjMCgASkwAgMVcBIDE3AkFiSgBITAkAiVkBQGIeCQaJuREIElMCQGISACQ2egJYvvfeqO93+p6vvDL0bop+iy5iXJfJxm+58cmvHrc0eCN35qYyTvqIcV0mHr/lxqde3ikBLB8+HK81Vz3m7dtD62r0W3Q14rpMPn6vrUuA7V61BvH6uKXZl8kfI65L43f7OwGXDx8MNdU+frZ299Y/teOwDDIOtloBRGn8uh31z+it9Vt0U8c1ShyWAcZvufHp2xvtASwf/HKIZvm1V4foIvZbdFPENWIclhXH77XWOy9yu1ppX5Z+ixqHZcV2dXQjUC+fg5xxLVWOKgEQnAQQogRYPrg/RBa1fVHb1Yqx+i96HJaV2tfXI8F6+izki2uZ/3N2VAKc6OmzkC+uZfYjeiQYJNbVE4F6+izki2up8DmVADQgRwIYqiSAnvq2p89CvriWwN8FWL367SGydfvq3+/fWr9FN1Zco8dhVWn8dlQC9PI5yBnXUuWorgJAYuXmZ7+10bcBD9/56RDN6s53hugi9lt0U8Q1YhxWFcfvxs8DWN15bYhk3Z76tX5r/RbdVHGNFodV5fG7VQkQpROjtKPX9vbaT1HisArQjq2fCbi683rVhq+PX//M3lq/RTdXXGvHYRVk/O70UNDVnTcqdd4bITqvtX6Lbu64rozfodx89rWdfxfg8P5PhrmsvvHdoRdz9lt0NeN6mHj8jpIApu7MaJ02hYzJIGJcD5ON33Lz2ddHTQBAOzq6ExDYlDsBIbG+HgkGbEQJAIktnP8hLysASMweACTmKgAkpgSAxCQASEwJAInZBITElACQmBIAErMCgMQkAEisr98GBDZiBQCJSQCQmKsAkJgbgSAxJQAktiguA0Ba9gAgMSUAJGYTEBJbzHmwo3v/Ovdv199UjYhDXUcJx2fZf+7tSX8b8OjePzf+f66/+YFJ2pKZOOiXs5T95+5OkgCO7v1j5/e4/uasC5QuiYN+uci106uAI7/GGHQnTt9ngvZleYmDfhkuGSNl/3P3RlsBHN39+zCV69/74GTv3Rtx0C9XdW2s082Ug+7E+v0DnFaDv8RBvwwbjJc+tzaB+VYAR3ePhjmsj1P/LBv1JQ76ZdhwzJT9z/9opz2Ao7f/Nszt+vefmf2Y0YmDftmGEgAS26kEqHHWObE+bv0ld5SXOOiXYcux0/CXgVptd2/EoeV+UQJAYmX/+R9vtQl49NZfh9qu/+BDQ3bioF920XAJcKLltvdEHFrtl0X8Jp6v5bb3RBza7RcrAJIM9RrKEF3bTwRque09EYdm+8VVAEhMCcAI4p/p6ihDt3cC7v3wI1Ubvj5+/bvwar/EQb8MO4wfJQAk1u4mYKvt7o04NN0vO30ZaO/wo1UavT5u/eV3lJc46Jdhy7HT6CZgi23ukTi03i877wHsHd4YpyVBj9cKcdAv1R4Jtnd4c5jD+jj1l9xRX+KgX4aNS4BGNitOtdTWnolDN/0y2mXAveXHxnqrKu/fC3HQL5soBy/8YvSfBnu0/Mto77W33B/tvbIRB/1ymXLwwv1Jfhvw0fLPO7/H3vJglLZkJg765SLl4MVpEsBjjw43TwR7KxNfHObxKPn4LAcvvjNpAnjSo8M/Db//xMtn/u3LX//dXM1I7yQO59lbfTxt//z23S+d+d+/+MdfddsvizLjTQvPrG4Nw7tn/23OdmR3GgeurOf+8mUgSCzQrcBR2gF5xmacG4GitAMSjU0lACSmBIBL9bsCkAAgcQJQAkBiNgEh8SagEgAu1W8CUAJAYlYAkHgFYA8AEu8BKAEgMSUAXKrfFYAEAJeSAGbQbyfTujL0ahHms0VpByQam7M+EegiUdoBmcamPQC4VL8JwGVASMwKABKvANwJCInvBFwMQbz/8y/UbgKkE6gEgKjK0CsJABIngHLrpV/P9tNgT3r/Z8/XOCxc2Ve++Yfue8sKABKe+R+TACBxAii3XvpNlRIAqM8KABKLcyMQMDvfBYDElACQmAQAiSkBIDGbgJBYmEeCAfNTAkBiNgEhMXsAkJgVACRmDwASswKAxCQASCzObwMCs7MCgMQkAEjMVQBIvgI42QXwXEDIp7gTEBJTAkBiNgEhMQkAEnt8I5CNQMjldOZ7IhAkpgSAxFwFgMSeXAHYB4Ac/jvp3QgEiT1dAvhyMPTtf+a4TUBITAKAxM66CqAMgD7939y2CQiJnVcCuCQIfTlzotsDgMQuuhPQXgD04dy5fNkegFIA2nbhBFcCQGJX+TKQUgDadOncveoKQCkAbbnSxN6kBJAEoA1XntSLi/cAgZ5tugloFQCxbTSht7kKIAlATGWuR4IpHCCWrebkLvcBWAlADFtP4l2/DSgJQF2l9lOBlQNQx85zb6xbgR+/iZ8Zh+mNdtId+7sASgKYVpnitwHHJAnANEafrVN9G1BJAOOZbJ9t6q8DWw3AbiadoIthelYDEPTq2pwPBJEIINhl9RqPBX/ygC4bwlDvXpo5SoCLWBWQWandgCjPBHy6EVYG9KgMwURJAE87q1GSAi0ptRtwFf8GgqTHlz/5/58AAAAASUVORK5CYII=")

EXPORTS_SUBDIR = "SubnetPlanner Reports"


class MainWindow:
    def __init__(self, root: tk.Tk, smoke: bool = False):
        self.root = root
        self.settings = self._load_settings()

        root.title(f"{APP_NAME} — Custom Subnet Calculator & VLSM Planner")
        root.geometry(self.settings.get("geometry", "1220x860"))
        root.minsize(1080, 720)
        root.configure(bg=T.BG)

        self._set_icon()

        # shared state
        self.current_subnet = None
        self.current_plan = None
        self.exported_paths = [p for p in self.settings.get("exported", [])
                               if os.path.exists(p)]
        self.export_dir = self.settings.get("export_dir",
                                            str(Path.home() / "Documents" /
                                                EXPORTS_SUBDIR))

        setup_style(root)

        self._build_header()
        self._build_notebook()
        self._build_statusbar()

        if not smoke:
            last_tab = int(self.settings.get("last_tab", 0))
            self.notebook.select(last_tab)
            self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---- construction ----------------------------------------------------
    def _set_icon(self):
        try:
            local = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                 "assets", "app.png")
            if os.path.exists(local):
                img = tk.PhotoImage(file=local)
            else:
                raw = base64.b64decode(_ICON_B64)
                data_uri = "data:image/png;base64," + _ICON_B64
                img = tk.PhotoImage(data=data_uri)
            self.root.tk.call("wm", "iconphoto", self.root._w, img)
        except tk.TclError:
            pass

    def _build_header(self):
        header = tk.Frame(self.root, bg=T.HEADER_BG)
        header.pack(fill="x")
        inner = tk.Frame(header, bg=T.HEADER_BG)
        inner.pack(fill="x", padx=24, pady=12)
        title = tk.Label(inner, text=APP_NAME, bg=T.HEADER_BG, fg=T.HEADER_FG,
                         font=T.FONT_TITLE)
        title.pack(anchor="w")
        sub = tk.Label(inner, text="Custom Subnet Calculator & VLSM Planner — "
                                   "works 100% offline",
                       bg=T.HEADER_BG, fg="#C7D2E0", font=T.FONT_SMALL)
        sub.pack(anchor="w", pady=(2, 0))

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=0, pady=0)

        self.subnet_page = SubnetPage(self.notebook, self)
        self.vlsm_page = VlsmPage(self.notebook, self)
        self.report_page = ReportPage(self.notebook, self)

        self.notebook.add(self.subnet_page, text="  Subnet Calculator  ")
        self.notebook.add(self.vlsm_page, text="  VLSM Planner  ")
        self.notebook.add(self.report_page, text="  Reports  ")
        self.notebook.bind("<<NotebookTabChanged>>",
                           lambda e: self.report_page.refresh())

    def _build_statusbar(self):
        bar = tk.Frame(self.root, bg="#E2E9F2")
        bar.pack(fill="x", side="bottom")
        self.status_label = ttk.Label(bar, text="Ready.", style="Status.TLabel",
                                      anchor="w")
        self.status_label.pack(fill="x", padx=14, pady=4)
        self.status_kind = "ok"

    # ---- public helpers ----------------------------------------------------
    def status(self, message: str, kind: str = "ok"):
        colors = {"ok": T.TEAL, "warn": T.WARN, "error": T.ER}
        fg = colors.get(kind, T.MUTED)
        self.status_label.configure(text=message, foreground=fg)
        self.status_kind = kind

    # ---- persistence -------------------------------------------------------
    def _load_settings(self) -> dict:
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def on_close(self):
        try:
            self.settings["geometry"] = self.root.geometry()
            self.settings["last_tab"] = self.notebook.index("current")
            self.settings["export_dir"] = self.export_dir
            self.settings["exported"] = self.exported_paths[-20:]
            SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
            with open(SETTINGS_FILE, "w", encoding="utf-8") as fh:
                json.dump(self.settings, fh, indent=2)
        except OSError:
            pass
        self.root.destroy()


def run(smoke: bool = False):
    root = tk.Tk()
    MainWindow(root, smoke=smoke)
    if not smoke:
        root.mainloop()
    else:
        root.update_idletasks()
        root.destroy()
    return 0


if __name__ == "__main__":
    raise SystemExit(run())