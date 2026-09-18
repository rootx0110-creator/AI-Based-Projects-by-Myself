"""Deleted File Recovery Tool - FAT/NTFS - entry point."""
import os
import sys
import traceback


def bootstrap():
    # Ensure app package is importable when frozen with PyInstaller
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)

    try:
        import customtkinter
    except ImportError as e:
        print("This application requires: pip install -r requirements.txt")
        print(f"Missing dependency: {e}")
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(
                    0, "Missing dependency. Please run:\n\npip install -r requirements.txt",
                    "Deleted File Recovery Tool", 0x10)
            except Exception:
                pass
        sys.exit(1)

    try:
        from app.ui.main_window import App
    except Exception:
        tk_err = traceback.format_exc()
        print("Failed to initialize UI:\n", tk_err)
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(
                    0, f"Application failed to start:\n{tk_err[:500]}",
                    "Deleted File Recovery Tool", 0x10)
            except Exception:
                pass
        sys.exit(1)

    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    app = App()
    app.run()


if __name__ == "__main__":
    bootstrap()