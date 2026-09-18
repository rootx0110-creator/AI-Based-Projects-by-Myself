"""Red Team Engagement Report Generator - entry point."""

import sys
import os


def _bootstrap():
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)


def main():
    _bootstrap()
    from app.gui import launch
    launch()


if __name__ == "__main__":
    main()