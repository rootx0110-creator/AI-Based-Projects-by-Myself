"""C2 Detection Lab.

A self-contained laboratory for building a lightweight HTTP command-and-control
(C2) beacon, generating Zeek and Suricata detection signatures that catch it,
running a detection pass over the simulated session, and exporting reports in
HTML.

This package is intentionally dependency-light so it can be packaged as a
single Windows executable with PyInstaller. Tkinter (standard library) drives
the GUI; `requests` drives the simulated beacon client.
"""

__title__ = "C2 Detection Lab"
__version__ = "1.0.0"