"""Standalone GUI entry point used only for PyInstaller builds.

Same reasoning as ``entry.py``: PyInstaller runs this as a top-level script,
so it cannot use the package's relative-import ``__main__``. Keep tiny.
"""

from arpscan.gui import main

if __name__ == "__main__":
    main()