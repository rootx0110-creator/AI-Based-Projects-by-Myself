"""Application entry point for the Threat Actor TTP Profiler."""

from __future__ import annotations

import os
import sys


def _log_dir() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, "ThreatActorTTPProfiler")
    os.makedirs(path, exist_ok=True)
    return path


def _log(msg: str) -> None:
    try:
        with open(os.path.join(_log_dir(), "startup.log"), "a", encoding="utf-8") as fh:
            fh.write("[%s] %s\n" % (os.path.basename(sys.argv[0]), msg))
    except Exception:  # noqa: BLE001
        pass


def main() -> int:
    import customtkinter as ctk  # noqa: PLC0415

    _log("main() enter; frozen=%s _MEIPASS=%s" % (getattr(sys, "frozen", False), getattr(sys, "_MEIPASS", None)))

    ctk.set_appearance_mode("dark")

    from .core.workbench import Workbench  # noqa: PLC0415
    from .ui.main_window import MainWindow  # noqa: PLC0415

    _log("constructing Workbench()")
    workbench = Workbench()
    _log("kb loaded: techniques=%d rules=%d actors=%d yara_native=%s data_dir=%s" % (
        len(workbench.attack_db.techniques), len(workbench.attack_db.rules),
        len(workbench.actor_db.all_actor_ids()), workbench.yara.is_native,
        workbench.yara.rules_path))
    _log("constructing MainWindow()")
    app = MainWindow(workbench)
    _log("entering mainloop")
    _run_demo(app) if os.environ.get("TTP_DEMO") else None
    app.mainloop()
    _log("mainloop exited cleanly")
    return 0


def _run_demo(app) -> None:
    import os
    import tempfile

    from .core.model import SampleResult

    def make_sample(name: str, lines: list, ftype: str = "plain") -> SampleResult:
        path = os.path.join(tempfile.gettempdir(), "ttp_demo_" + name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        return SampleResult(
            filepath=path, filename=name, size_bytes=os.path.getsize(path),
            file_type=ftype, strings=list(lines), md5="x", sha1="x", sha256="x",
            imports={"kernel32.dll": ["CreateRemoteThread", "VirtualAllocEx", "GetProcAddress"],
                     "advapi32.dll": ["OpenProcessToken", "RegSetValueEx"]},
            dlls=["kernel32.dll", "advapi32.dll", "wininet.dll"],
        )

    wb = app.workbench
    wb.samples.append(make_sample("a.txt", [
        "http://evil.example/panel.php", "powershell -enc AAA", "sekurlsa::logonpasswords",
        "schtasks /create", "vssadmin delete shadows"]))
    wb.samples.append(make_sample("b.txt", [
        "https://gist.github.com/exfil", "WanaCrypt0r", "bitcoin", "139.59.1.1:443"]))
    try:
        wb.reanalyze()
    except Exception as exc:  # noqa: BLE001
        app.set_status("demo analysis failed: %s" % exc)
        return

    shot_dir = os.path.join(tempfile.gettempdir(), "ttp_exe_shots")
    os.makedirs(shot_dir, exist_ok=True)
    state = {"idx": 0, "page": "dashboard"}

    def _snap() -> None:
        from PIL import ImageGrab

        app.show_page(state["page"])
        try:
            app.update()
        except Exception:  # noqa: BLE001
            pass
        try:
            x = app.winfo_rootx(); y = app.winfo_rooty()
            w = app.winfo_width(); h = app.winfo_height()
            ImageGrab.grab((x, y, x + w, y + h)).save(
                os.path.join(shot_dir, state["page"] + ".png"))
        except Exception as exc:  # noqa: BLE001
            pass

    pages = ["dashboard", "samples", "attack", "actors", "navigator", "reports", "settings"]

    def _next() -> None:
        if state["idx"] >= len(pages):
            app._on_close()
            return
        state["page"] = pages[state["idx"]]
        state["idx"] += 1
        _snap()
        app.after(500, _next)

    app.after(1200, _next)


def _fail(exc: Exception) -> int:
    import traceback  # noqa: PLC0415

    try:
        _log("STARTUP FAILED:\n%s" % "".join(traceback.format_exception(exc)))
    except Exception:  # noqa: BLE001
        pass
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Threat Actor TTP Profiler",
            "The application failed to start:\n\n%s\n\nDetails were written to:\n%s"
            % (exc, os.path.join(_log_dir(), "startup.log")),
        )
        root.destroy()
    except Exception:  # noqa: BLE001
        print("FATAL:", exc)
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        sys.exit(_fail(exc))