"""Application launcher.

Run directly:  python run.py
Or build the exe with the included build_exe.bat / PyInstaller specs.
"""

import sys


def main() -> int:
    from toolkit.ui.app import SolverApp
    app = SolverApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())