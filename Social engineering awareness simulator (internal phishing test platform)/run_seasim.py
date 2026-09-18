"""Entry script for the packaged SeaSim executable (PyInstaller)."""

import sys
from pathlib import Path

# When frozen, ensure the project root is importable (onefile layout).
if getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(sys.executable).resolve().parent))

from seasim.app import main

if __name__ == "__main__":
    main()
