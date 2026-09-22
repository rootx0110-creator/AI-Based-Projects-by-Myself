"""Purple Team Capstone - entry point.

GUI:        python main.py          (or run the built executable)
Headless:   python main.py --cli
Self-test:  python main.py --selftest
Docs:       python main.py --docs
"""

from __future__ import annotations

import sys

from purpleteam.__main__ import main

if __name__ == "__main__":
    sys.exit(main())