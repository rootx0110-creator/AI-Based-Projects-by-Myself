"""Custom Proxy Server — application entry point."""

from __future__ import annotations

import sys


def main() -> int:
    from custom_proxy.gui import run_gui
    run_gui()
    return 0


if __name__ == "__main__":
    if getattr(sys, "frozen", False):
        # Run GUI from the bundled app (no console output expected).
        pass
    sys.exit(main())
