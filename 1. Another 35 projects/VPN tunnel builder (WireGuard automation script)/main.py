"""VPN Tunnel Builder - application entry point.

Run the GUI:        python main.py
Run engine tests:   python -m wgbuilder.core.selfcheck
"""

import sys

from wgbuilder.app import run


def main():
    data_folder = None
    args = sys.argv[1:]
    if args and args[0] == "--data":
        data_folder = args[1] if len(args) > 1 else None
    run(data_folder=data_folder)


if __name__ == "__main__":
    main()