"""Standalone entry point used only for PyInstaller builds.

PyInstaller executes this file as a top-level script, so the package's
``__main__.py`` (which uses a relative import) cannot be used as the build
entry. Keep this file tiny; all logic lives in ``arpscan.cli``.
"""

import sys

from arpscan.cli import main

if __name__ == "__main__":
    sys.exit(main())