"""SubnetPlanner entry point."""

import sys

from app.gui import run

APP_VERSION = "1.0.0"

if __name__ == "__main__":
    if "--debug" in sys.argv:
        import traceback
        try:
            print("DEBUG: importing gui", file=sys.stderr, flush=True)
            import tkinter as tk
            from app.gui import MainWindow
            root = tk.Tk()
            MainWindow(root)
            root.update_idletasks()
            root.update()
            print("DEBUG: viewable=", root.winfo_viewable(),
                  file=sys.stderr, flush=True)
            root.mainloop()
        except Exception:
            traceback.print_exc()
            sys.exit(1)
    sys.exit(run())