#!/usr/bin/env python3
"""LBSimulator — Load Balancer Simulator with Health Checks.

Entry point: launches the PyQt6 GUI application.
"""

import sys
import os

def _setup_path():
    """Ensure src package is importable in both dev and bundled scenarios."""
    # PyInstaller creates a temp folder and stores path in _MEIPASS
    if getattr(sys, 'frozen', False):
        # Running as bundled executable
        base_path = sys._MEIPASS
    else:
        # Running in development
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    # Add the base path (which contains 'src' folder) to sys.path
    if base_path not in sys.path:
        sys.path.insert(0, base_path)

_setup_path()

from src.gui.app import main

if __name__ == "__main__":
    main()
