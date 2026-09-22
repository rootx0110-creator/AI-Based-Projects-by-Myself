"""Entry point used when freezing to a single EXE with PyInstaller."""

import multiprocessing
import os

from app.server import run

if __name__ == "__main__":
    multiprocessing.freeze_support()
    # Set CS_NO_BROWSER=1 to start the server without opening a browser tab
    run(host="127.0.0.1", port=9999, open_browser=os.environ.get("CS_NO_BROWSER") != "1")
