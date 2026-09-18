#!/usr/bin/env python3
"""Convenience launcher.

    python run.py                 -> GUI
    python run.py --cli scan      -> headless scan
    python run.py --cli rules     -> list rules
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hardening_checker.__main__ import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
