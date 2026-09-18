#!/usr/bin/env python3
"""VaultGuard entry point."""
from __future__ import annotations

import os
import sys


def resource_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def main():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from ui.app import main as app_main

    app_main()


if __name__ == "__main__":
    main()