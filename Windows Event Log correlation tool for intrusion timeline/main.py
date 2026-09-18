"""Entry point for the Windows Event Log Correlation Tool."""
from __future__ import annotations

import sys


def main() -> int:
    try:
        from app.gui import launch
    except Exception as exc:  # noqa: BLE001
        import tkinter as tk
        from tkinter import messagebox
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Startup error", str(exc))
            root.destroy()
        except Exception:  # noqa: BLE001
            sys.stderr.write(f"Startup error: {exc}\n")
        return 1
    launch()
    return 0


if __name__ == "__main__":
    sys.exit(main())